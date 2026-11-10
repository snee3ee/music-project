"""Streaming reconstructed peaks, with explicit FIR, delay and zero-extension scope."""

import numpy as np
from scipy.signal import firwin, lfilter

# ITU-R BS.1770-5 Annex2, 48-tap four-phase interpolation coefficients.
ITU_PHASES = np.array(
    [
        [0.001708984375, -0.0291748046875, -0.0189208984375, -0.00830078125],
        [0.010986328125, 0.029296875, 0.0330810546875, 0.014892578125],
        [-0.0196533203125, -0.0517578125, -0.0582275390625, -0.026611328125],
        [0.033203125, 0.089111328125, 0.1015625, 0.047607421875],
        [-0.0594482421875, -0.16650390625, -0.2003173828125, -0.102294921875],
        [0.1373291015625, 0.465087890625, 0.77978515625, 0.97216796875],
        [0.97216796875, 0.77978515625, 0.465087890625, 0.1373291015625],
        [-0.102294921875, -0.2003173828125, -0.16650390625, -0.0594482421875],
        [0.047607421875, 0.1015625, 0.089111328125, 0.033203125],
        [-0.026611328125, -0.0582275390625, -0.0517578125, -0.0196533203125],
        [0.014892578125, 0.0330810546875, 0.029296875, 0.010986328125],
        [-0.00830078125, -0.0189208984375, -0.0291748046875, 0.001708984375],
    ]
)
TP_RATES = {44100, 48000, 88200, 96000, 176400, 192000}


class TruePeak:
    def __init__(self, rate: int, channels: int):
        self.rate, self.channels = rate, channels
        if rate == 44100:
            self.factor = 8
            h = firwin(385, 1 / 8, window=("kaiser", 8.6)) * 8
            self.phases = [h[p::8] for p in range(8)]
            self.delay = 192 / 8
            self.filter_name = "385-tap Kaiser8.6 polyphase FIR"
        else:
            self.factor = 4
            self.phases = [ITU_PHASES[:, p] for p in range(4)]
            self.delay = 23.5 / 4
            self.filter_name = "ITU-R BS.1770-5 Annex2 48-tap four-phase FIR"
        self.states = [np.zeros((len(h) - 1, channels)) for h in self.phases]
        self.peak = np.zeros(channels)
        self.times = [None] * channels
        self.frames = 0
        self.input_frames = None

    def consume(self, x):
        for phase, h in enumerate(self.phases):
            y, self.states[phase] = lfilter(h, [1], x, axis=0, zi=self.states[phase])
            times = (self.frames + np.arange(len(x)) + phase / self.factor - self.delay) / self.rate
            valid = times >= 0
            if self.input_frames is not None:
                valid &= times <= self.input_frames / self.rate
            indices = np.flatnonzero(valid)
            if len(indices):
                absolute = abs(y[indices])
                for ch in range(self.channels):
                    value = float(np.max(absolute[:, ch]))
                    index = int(np.flatnonzero(absolute[:, ch] >= value * (1 - 1e-12))[0])
                    time = float(times[indices[index]])
                    tolerance = 1e-12 * max(value, float(self.peak[ch]), 1e-300)
                    if value > self.peak[ch] + tolerance:
                        self.times[ch] = time
                    elif abs(value - self.peak[ch]) <= tolerance and (
                        self.times[ch] is None or time < self.times[ch]
                    ):
                        self.times[ch] = time
                    self.peak[ch] = max(self.peak[ch], value)
        self.frames += len(x)

    def finish(self):
        self.input_frames = self.frames
        self.consume(np.zeros((max(len(h) for h in self.phases), self.channels)))
        return {
            "peak_linear_per_channel": self.peak.tolist(),
            "time_seconds_per_channel": self.times,
            "oversampling_factor": self.factor,
            "output_rate_hz": self.rate * self.factor,
            "filter": self.filter_name,
            "group_delay_input_frames": self.delay,
            "boundary": "Zero extension; only reconstructed times inside [0,decoded duration]",
            "validation_status": "Generated controls; not a blanket standards-compliance certification",
            "tested_rate": self.rate in TP_RATES,
            "time_grid_seconds": 1 / (self.rate * self.factor),
            "earliest_peak_tie_relative_tolerance": 1e-12,
        }
