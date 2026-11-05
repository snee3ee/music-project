"""Bounded summaries of PSD cells, reusing existing periodograms without extra FFTs."""

import numpy as np

from music_project.core.origin_features import boundary_features, noise_features


class OriginCollector:
    def __init__(self, rate: int, channels: int, nfft: int = 16384, maximum_noise_hz=160000):
        self.rate, self.channels, self.nfft = rate, channels, nfft
        self.hop = nfft // 2
        self.f = np.fft.rfftfreq(nfft, 1 / rate)
        self.sum = np.zeros((nfft // 2 + 1, channels))
        self.count = 0
        self.seen = 0
        self.start = 0.0
        self.window_number = 0
        self.cells = []
        self.total_cells = 0
        self.max_cells = 64
        self.target = max(1, round(rate / self.hop))
        self.errors = []
        self.maximum_noise_hz = maximum_noise_hz

    def start_window(self, start):
        self.start = float(start)
        self.window_number += 1
        self.seen = 0

    def consume(self, periodogram):
        self.sum += periodogram
        self.count += 1
        self.seen += 1
        if self.count >= self.target:
            self.flush()

    def flush(self):
        if not self.count:
            return
        mean = self.sum / self.count
        self.total_cells += 1
        try:
            boundaries = boundary_features(self.f, mean)
            noise = noise_features(self.f, mean, self.maximum_noise_hz)
        except (ValueError, FloatingPointError) as exc:
            self.errors = [str(exc)]
            self.sum.fill(0)
            self.count = 0
            return
        cell = {
            "window": self.window_number,
            "start_seconds": self.start + (self.seen - self.count) * self.hop / self.rate,
            "end_seconds": self.start + ((self.seen - 1) * self.hop + self.nfft) / self.rate,
            "fft_segments": self.count,
            "boundaries": boundaries,
            "noise": noise,
        }
        # Bounded progressive thinning; this is not a uniform random sample of time.
        self.cells.append(cell)
        if len(self.cells) > self.max_cells:
            self.cells = self.cells[::2]
        self.sum.fill(0)
        self.count = 0

    def end_window(self):
        self.flush()

    def result(self):
        self.flush()
        return {
            "cells": self.cells,
            "measured_cells": self.total_cells,
            "retained_cells": len(self.cells),
            "retention": "deterministic thinning by 2 at >64 cells; inference describes retained cells",
            "time_definition": "support of complete overlapping FFT segments; windows may overlap by one half FFT",
            "new_fft_computations": 0,
            "errors": self.errors,
        }
