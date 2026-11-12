"""Bounded PCM investigation in the existing decode; no historical codec classifier."""

import math
from collections import Counter

import numpy as np

from music_project.core.dsd_spectrum import StreamingWelch
from music_project.core.lossy_models import LOSSY_VERSION, LossyReport
from music_project.core.lossy_spectrum import (
    LOSSY_BOUNDARY_RULE,
    band_measurements,
    measure_candidates,
)
from music_project.core.models import Finding
from music_project.core.origin_features import boundary_features

ADDITIONAL = [
    {
        "family": "Time-frequency discontinuities / transform structures",
        "status": "Unsupported",
        "reason": "No independently validated codec discrimination; transients, tones and editing are alternatives.",
    },
    {
        "family": "Pre-echo / coding noise",
        "status": "Unsupported",
        "reason": "Reference-free attribution is not validated; linear-phase filtering and existing noise are counterexamples.",
    },
]


def applicable(info):
    if info.kind != "PCM" or not info.lossless:
        return "PCM-only investigation of decoded lossless streams; native DSD/current lossy codecs excluded"
    if info.channels not in (1, 2):
        return "Mono/stereo only; multichannel investigation not validated"
    if info.sample_rate not in {32000, 44100, 48000, 88200, 96000, 176400, 192000}:
        return "Native PCM rate outside evaluated32/44.1/48/88.2/96/176.4/192kHz configurations"
    return ""


def report_finding(report):
    return Finding(
        "Measured" if report.performed else "Not evaluated",
        report.reason,
        report.to_dict(),
        method="Native-rate per-channel Welch, adaptive side-band contrasts and explicit temporal eligibility",
        limitations=report.limitations,
        method_version=LOSSY_VERSION,
    )


def unavailable(reason):
    return report_finding(LossyReport(reason=reason, additional_indicators=ADDITIONAL))


def bandwidth_observed(report):
    candidates = report.candidates if isinstance(report, LossyReport) else report["candidates"]
    return any(c["detected"] for b in candidates for c in b["channels"]) or any(
        s["detected_windows"] for b in candidates for s in b["stability"]
    )


class LossyCollector:
    """At most32 selected2s slots; native PCM/FFT buffers stay independent of duration."""

    def __init__(self, info, available_seconds=None):
        self.info = info
        self.rate, self.channels = info.sample_rate, info.channels
        self.disabled = applicable(info)
        self.frames = self.segments = self.selected_frames = 0
        self.rows = []
        self.window_psd = []
        self.index = 0
        self.current = None
        self.nfft = 8192
        self.total = None if self.disabled else np.zeros((4097, self.channels))
        self.f = None if self.disabled else np.fft.rfftfreq(self.nfft, 1 / self.rate)
        seconds = available_seconds if available_seconds is not None else info.duration
        self.known_duration = seconds is not None and math.isfinite(seconds) and seconds > 0
        if self.disabled:
            self.plan, self.slots = [], 0
        elif self.known_duration:
            frames = round(seconds * self.rate)
            self.slots = max(1, frames // (2 * self.rate))
            chosen = np.unique(
                np.rint(np.linspace(0, self.slots - 1, min(32, self.slots))).astype(int)
            )
            self.plan = [
                (int(i) * 2 * self.rate, min(frames, (int(i) + 1) * 2 * self.rate)) for i in chosen
            ]
        else:
            self.slots = 32
            self.plan = [(i * 2 * self.rate, (i + 1) * 2 * self.rate) for i in range(32)]

    def _start(self):
        self.current = StreamingWelch(self.rate, self.channels, self.nfft)
        self.squares = np.zeros(self.channels)
        self.count = 0
        self.energy_sum = np.zeros(self.channels)
        self.energy_squared = np.zeros(self.channels)
        self.energy_count = 0

        def energy(p):
            e = p.sum(axis=0) * self.rate / self.nfft
            self.energy_sum += e
            self.energy_squared += e**2
            self.energy_count += 1

        self.current.segment_consumer = energy

    def consume(self, samples):
        first, last = self.frames, self.frames + len(samples)
        if not self.disabled:
            while self.index < len(self.plan):
                start, end = self.plan[self.index]
                if start >= last:
                    break
                if end <= first:
                    self.index += 1
                    continue
                if self.current is None:
                    self._start()
                selected = samples[max(0, start - first) : min(len(samples), end - first)]
                self.current.consume(selected)
                self.squares += np.sum(selected**2, axis=0)
                self.count += len(selected)
                if last < end:
                    break
                self._flush()
                self.index += 1
        self.frames = last

    def _flush(self):
        if self.current is None:
            return
        start = self.plan[self.index][0]
        row = {
            "window": self.index + 1,
            "start_seconds": start / self.rate,
            "end_seconds": (start + self.count) / self.rate,
            "frames": self.count,
            "fft_segments": self.current.segments,
            "channels": [],
            "candidates": [],
        }
        if self.count < self.rate or not self.current.segments:
            row.update(status="Discarded", reason="Less than1s or no complete FFT support")
        else:
            p = self.current.total / self.current.segments
            ref = (self.f >= 1000) & (self.f <= 8000)
            for ch in range(self.channels):
                rms = float(np.sqrt(self.squares[ch] / self.count))
                reference = float(np.mean(p[ref, ch]))
                occupancy = float(np.mean(p[ref, ch] > reference * 1e-3)) if reference else 0
                reason = (
                    "silence"
                    if rms == 0
                    else "low_energy"
                    if rms < 1e-4
                    else "sparse_band_excitation"
                    if occupancy < 0.5 or reference <= 1e-16
                    else "eligible"
                )
                mean_e = self.energy_sum[ch] / self.energy_count
                cv = (
                    float(
                        np.sqrt(max(0, self.energy_squared[ch] / self.energy_count - mean_e**2))
                        / mean_e
                    )
                    if mean_e
                    else None
                )
                row["channels"].append(
                    {
                        "channel": ch + 1,
                        "eligibility": reason,
                        "rms_dbfs": float(20 * np.log10(rms)) if rms else None,
                        "reference_occupancy": occupancy,
                        "segment_energy_cv": cv,
                        "dominant_bin_power_fraction": float(np.max(p[:, ch]) / np.sum(p[:, ch]))
                        if np.sum(p[:, ch])
                        else None,
                    }
                )
            row["status"] = "Measured"
            row["candidates"] = measure_candidates(self.f, p)
            self.window_psd.append((row, p))
            self.total += self.current.total
            self.segments += self.current.segments
            self.selected_frames += self.count
        self.rows.append(row)
        self.current = None

    def finish(self, *, complete_decode=False, fallback_reason=""):
        self._flush()
        if self.disabled:
            return unavailable(self.disabled)
        eligible = [
            r for r in self.rows if any(c["eligibility"] == "eligible" for c in r["channels"])
        ]
        report = LossyReport(
            performed=bool(self.segments),
            windows=self.rows,
            additional_indicators=ADDITIONAL,
            scope={
                "domain": "Native-rate decoded lossless PCM",
                "analyzed_seconds": self.selected_frames / self.rate,
                "decoded_seconds": self.frames / self.rate,
                "total_seconds": self.info.duration,
                "complete_file": complete_decode and self.selected_frames == self.frames,
                "complete_stream_decoded": complete_decode,
                "ranges": [
                    {"start_seconds": r["start_seconds"], "end_seconds": r["end_seconds"]}
                    for r in self.rows
                    if r["status"] == "Measured"
                ],
                "fallback_reason": fallback_reason,
            },
            parameters={
                "nfft": self.nfft,
                "window": "periodic Hann",
                "overlap": "50%",
                "detrend": False,
                "sample_rate_hz": self.rate,
                "frequency_step_hz": self.rate / self.nfft,
                "window_seconds": 2,
                "max_windows": 32,
                "minimum_seconds": 1,
                "selection": "uniform rounded2s slot indexes over known duration; no FFT spans gaps"
                if self.known_duration
                else "unknown duration: first32 two-second slots",
                "search_hz": [8000, min(24000, self.rate / 2 - 600)],
                "edge_policy": "Last600Hz below Nyquist cannot establish a two-sided cutoff",
                "eligibility": "RMS>=-80dBFS, reference1-8kHz meanPSD>1e-16 and occupancy>=0.5 above reference-30dB",
                "threshold_status": "Exploratory observation guards; not a historical-codec decision rule",
            },
            counts={
                "planned_windows": len(self.plan),
                "seen_windows": len(self.rows),
                "eligible_windows": len(eligible),
                "discarded_windows": len(self.rows) - len(eligible),
                "unreached_windows": len(self.plan) - len(self.rows),
                "unselected_slots": self.slots - len(self.plan),
                "discard_reasons": dict(
                    Counter(
                        c["eligibility"]
                        for r in self.rows
                        for c in r["channels"]
                        if c["eligibility"] != "eligible"
                    )
                ),
                "reason_count_unit": "channel-windows; discarded_windows counts windows with no eligible channel",
            },
        )
        if self.segments:
            p = self.total / self.segments
            report.bands = band_measurements(self.f, p)
            # A region-specific boundary can disappear in the average. Retain
            # discoveries from windows before global candidates and remeasure
            # the exact same frequencies in every retained window (no extra FFT).
            frequencies = []
            for row in self.rows:
                for b in row["candidates"]:
                    if any(c["detected"] for c in b["channels"]) and all(
                        abs(b["candidate_hz"] - f) >= 600 for f in frequencies
                    ):
                        frequencies.append(b["candidate_hz"])
            discovered = len(frequencies)
            for b in measure_candidates(self.f, p):
                if all(abs(b["candidate_hz"] - f) >= 600 for f in frequencies):
                    frequencies.append(b["candidate_hz"])
            report.candidates = boundary_features(
                self.f, p, candidates=frequencies[:12], rule=LOSSY_BOUNDARY_RULE
            )
            report.parameters["candidate_retention"] = (
                "first12 distinct600Hz-separated window-positive frequencies, then global candidates; chronology order, not confidence"
            )
            report.counts["unretained_positive_candidate_clusters"] = max(0, discovered - 12)
            for row, density in self.window_psd:
                row["matched_candidates"] = boundary_features(
                    self.f,
                    density,
                    candidates=[b["candidate_hz"] for b in report.candidates],
                    rule=LOSSY_BOUNDARY_RULE,
                )
            report.spectrum = {
                "frequencies_hz": self.f.tolist(),
                "density_fs2_per_hz": p.tolist(),
                "normalization": "one-sided FS^2/Hz; no downmix",
            }
            for b in report.candidates:
                b["distance_to_nyquist_hz"] = self.rate / 2 - b["candidate_hz"]
                b["upper_support_hz"] = b["candidate_hz"] + 600
                b["stability"] = []
                for ch in range(self.channels):
                    valid = [r for r in eligible if r["channels"][ch]["eligibility"] == "eligible"]
                    hits = [
                        r
                        for r in valid
                        if any(
                            q["candidate_hz"] == b["candidate_hz"] and q["channels"][ch]["detected"]
                            for q in r["matched_candidates"]
                        )
                    ]
                    b["stability"].append(
                        {
                            "channel": ch + 1,
                            "eligible_windows": len(valid),
                            "detected_windows": len(hits),
                            "window_ids": [r["window"] for r in hits],
                            "recurrent": len(hits) >= 2 and len(hits) >= len(valid) / 2,
                            "maximum_window_drop_db": max(
                                (
                                    q["channels"][ch]["attenuation_db"]
                                    for r in hits
                                    for q in r["matched_candidates"]
                                    if q["candidate_hz"] == b["candidate_hz"]
                                    and q["channels"][ch]["attenuation_db"] is not None
                                ),
                                default=None,
                            ),
                        }
                    )
            observed = bandwidth_observed(report)
            report.classification = (
                "Inconclusive"
                if observed or len(eligible) < 2
                else "No evaluated indicators detected"
            )
            report.reason = (
                "Abrupt spectral suppression observed; filtering/band-limited lossless signals remain indistinguishable"
                if observed
                else "No evaluated abrupt spectral boundary; this does not establish lossless history"
                if len(eligible) >= 2
                else "Measured data have insufficient eligible temporal support for an encoding-history distinction"
            )
        else:
            report.reason = "No complete eligible-duration spectral window; record too short or decoding did not reach planned regions"
        return report_finding(report)


def investigate_context(context, *, reason="Existing decoded prefix fallback"):
    collector = LossyCollector(
        context.info, available_seconds=len(context.samples) / context.info.sample_rate
    )
    collector.consume(context.samples)
    return collector.finish(fallback_reason=reason)
