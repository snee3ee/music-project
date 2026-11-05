"""Streaming per-channel Welch density of explicitly converted PCM, never native DSD."""

import numpy as np
from scipy.signal.windows import hann

from music_project.core.models import AudioError

BANDS = (
    (20, 200),
    (200, 2000),
    (2000, 5000),
    (5000, 10000),
    (10000, 20000),
    (20000, 30000),
    (30000, 40000),
    (40000, 60000),
    (60000, 80000),
    (80000, 100000),
    (100000, 140000),
)


def power_db(power: float) -> float | None:
    """None represents exact zero (-infinity), without flooring low-level signals."""
    return float(10 * np.log10(power)) if power > 0 else None


class StreamingWelch:
    def __init__(self, rate: int, channels: int, nfft: int = 16384, segment_consumer=None):
        if rate <= 0 or not 1 <= channels <= 2 or nfft < 16 or nfft % 2:
            raise AudioError("Invalid Welch parameters")
        self.rate, self.channels, self.nfft = rate, channels, nfft
        self.hop = nfft // 2
        self.window = hann(nfft, sym=False)
        self.scale = 1 / (rate * np.sum(self.window**2))
        self.total = np.zeros((nfft // 2 + 1, channels), dtype=np.float64)
        self.pending = np.empty((0, channels), dtype=np.float64)
        self.segments = 0
        self.frames = 0
        self.max_buffer_frames = 0
        self.discarded_tail_frames = 0
        self.segment_consumer = segment_consumer

    def consume(self, samples: np.ndarray):
        samples = np.asarray(samples, dtype=np.float64)
        if samples.ndim != 2 or samples.shape[1] != self.channels or not np.isfinite(samples).all():
            raise AudioError("Non-finite or inconsistent converted PCM channels")
        # Also bound callers passing a very large array; no whole-array concatenation.
        for offset in range(0, len(samples), self.nfft):
            block = samples[offset : offset + self.nfft]
            self.frames += len(block)
            data = np.concatenate((self.pending, block))
            self.max_buffer_frames = max(self.max_buffer_frames, len(data))
            start = 0
            while start + self.nfft <= len(data):
                transformed = np.fft.rfft(
                    data[start : start + self.nfft] * self.window[:, None], axis=0
                )
                density = np.abs(transformed) ** 2 * self.scale
                density[1:-1] *= 2
                self.total += density
                if self.segment_consumer:
                    self.segment_consumer(density)
                self.segments += 1
                start += self.hop
            self.pending = data[start:].copy()

    def end_window(self):
        # Never construct an FFT spanning disjoint time ranges.
        self.discarded_tail_frames += len(self.pending)
        self.pending = np.empty((0, self.channels), dtype=np.float64)

    def result(self) -> dict:
        if not self.segments:
            return {
                "status": "Unknown",
                "reason": "Insufficient PCM for one complete FFT window",
                "frames": self.frames,
                "segments": 0,
            }
        psd = self.total / self.segments
        frequencies = np.fft.rfftfreq(self.nfft, 1 / self.rate)
        df = self.rate / self.nfft
        bands = []
        for low, high in BANDS:
            selected = (frequencies >= low) & (frequencies < high)
            available = high <= self.rate / 2 and bool(np.any(selected))
            powers = np.sum(psd[selected], axis=0) * df if available else None
            medians = np.median(psd[selected], axis=0) if available else None
            bands.append(
                {
                    "low_hz": low,
                    "high_hz": high,
                    "status": "Measured" if available else "Unsupported",
                    "reason": "PCM-derived; native DSD band response Not validated"
                    if available
                    else "Band exceeds converted Nyquist or FFT resolution",
                    "power_fs2": powers.tolist() if available else None,
                    "power_db_re_fs2": [power_db(p) for p in powers] if available else None,
                    "median_density_db_re_fs2_per_hz": [power_db(p) for p in medians]
                    if available
                    else None,
                    "left_minus_right_db": power_db(powers[0] / powers[1])
                    if available and self.channels == 2 and np.all(powers > 0)
                    else None,
                }
            )
        return {
            "status": "Measured",
            "domain": "DSD-to-PCM derived",
            "sample_rate_hz": self.rate,
            "channels": self.channels,
            "nfft": self.nfft,
            "overlap_frames": self.hop,
            "window": "periodic Hann",
            "detrend": False,
            "averaging": "linear power, per channel",
            "density_units": "FS^2/Hz; dB = 10 log10(density / (1 FS^2/Hz))",
            "power_units": "FS^2; dB = 10 log10(power / 1 FS^2); full-scale sine = -3.0103 dB",
            "zero_power_encoding": "null dB with linear zero means -infinity; no artificial floor",
            "frequency_step_hz": df,
            "nyquist_hz": self.rate / 2,
            "segments": self.segments,
            "frames": self.frames,
            "max_buffer_frames": self.max_buffer_frames,
            "discarded_tail_frames": self.discarded_tail_frames,
            "frequencies_hz": frequencies.tolist(),
            "density_fs2_per_hz": psd.tolist(),
            "bands": bands,
            "native_dsd_frequency_response": "Not validated",
        }
