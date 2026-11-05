"""Bounded direct one-bit DSF/DFF reads, without PCM conversion or provenance claims."""

import math
from collections.abc import Iterator

import numpy as np

from music_project.core.dsd_container import DSDContainer
from music_project.core.dsd_spectrum import StreamingWelch
from music_project.core.models import AudioError, AudioInfo


def native_blocks(
    info: AudioInfo, structure: DSDContainer, start: float, duration: float
) -> Iterator[np.ndarray]:
    if (
        structure.status != "Passed"
        or structure.compression != "DSD"
        or info.channels not in (1, 2)
    ):
        raise AudioError(
            "Unsupported: direct bitstream reader requires validated mono/stereo uncompressed DSF/DFF"
        )
    first = max(0, int(start * structure.rate))
    last = min(structure.samples_per_channel, first + int(duration * structure.rate))
    if first >= last or structure.audio_data_offset is None:
        raise AudioError("Empty native DSD window")
    with open(info.path, "rb") as source:
        if structure.container == "DSF":
            # DSF uses groups of 4096 bytes per channel, not interleaved individual bytes.
            group = first // 32768
            while group * 32768 < last:
                source.seek(structure.audio_data_offset + group * 4096 * info.channels)
                packed = source.read(4096 * info.channels)
                if len(packed) != 4096 * info.channels:
                    raise AudioError("Truncated native DSF block")
                bits = np.unpackbits(
                    np.frombuffer(packed, dtype=np.uint8).reshape(info.channels, 4096),
                    axis=1,
                    bitorder=structure.bit_order,
                ).T
                low, high = max(0, first - group * 32768), min(32768, last - group * 32768)
                yield bits[low:high].astype(np.float64) * 2 - 1
                group += 1
        elif structure.container == "DFF":
            byte_frame = first // 8
            while byte_frame * 8 < last:
                count = min(4096, math.ceil((last - byte_frame * 8) / 8))
                source.seek(structure.audio_data_offset + byte_frame * info.channels)
                packed = source.read(count * info.channels)
                if len(packed) != count * info.channels:
                    raise AudioError("Truncated native DFF block")
                raw = np.frombuffer(packed, dtype=np.uint8).reshape(count, info.channels, 1)
                bits = (
                    np.unpackbits(raw, axis=2, bitorder="big")
                    .transpose(0, 2, 1)
                    .reshape(-1, info.channels)
                )
                low, high = max(0, first - byte_frame * 8), min(len(bits), last - byte_frame * 8)
                yield bits[low:high].astype(np.float64) * 2 - 1
                byte_frame += count
        else:
            raise AudioError("Unsupported native container")


def native_spectra(info: AudioInfo, structure: DSDContainer, *, cancelled=None) -> dict:
    duration = structure.duration
    if not duration:
        raise AudioError("Native duration unavailable")
    width = min(0.25, duration / 3)
    starts = (
        [0.0]
        if duration < 1
        else [min(0.5, duration - width), (duration - width) / 2, max(0, duration - 0.5 - width)]
    )
    nfft = min(524288, max(4096, 2 ** math.ceil(math.log2(info.sample_rate / 64))))
    records = []
    for start in starts:
        estimator = StreamingWelch(info.sample_rate, info.channels, nfft)
        sums = np.zeros(info.channels)
        lag = np.zeros(info.channels)
        previous = None
        count = pairs = 0
        for block in native_blocks(info, structure, start, width):
            if cancelled and cancelled():
                raise AudioError("Cancelled: native bitstream investigation")
            estimator.consume(block)
            sums += block.sum(axis=0)
            count += len(block)
            lag += np.sum(block[1:] * block[:-1], axis=0)
            pairs += max(0, len(block) - 1)
            if previous is not None:
                lag += previous * block[0]
                pairs += 1
            previous = block[-1]
        if not estimator.segments:
            continue
        frequencies = np.fft.rfftfreq(nfft, 1 / info.sample_rate)
        selected = frequencies <= 160000
        records.append(
            {
                "start_seconds": start,
                "duration_seconds": count / info.sample_rate,
                "frames": count,
                "segments": estimator.segments,
                "frequencies_hz": frequencies[selected].tolist(),
                "density_fs2_per_hz": (estimator.total[selected] / estimator.segments).tolist(),
                "one_fraction_per_channel": ((sums / count + 1) / 2).tolist(),
                "lag1_sign_product_per_channel": (lag / pairs).tolist() if pairs else None,
            }
        )
    return {
        "status": "Measured" if records else "Unknown",
        "domain": "Native DSD bits mapped to -1/+1",
        "scope": "sampled native windows, independent of full converted-stream coverage",
        "windows": records,
        "nfft": nfft,
        "window": "periodic Hann",
        "overlap": "50%",
        "sample_rate_hz": info.sample_rate,
        "frequency_step_hz": info.sample_rate / nfft,
        "normalization": "one-sided FS^2/Hz, no detrend; no decimation or resampling",
        "classification": "Bit density/autocorrelation are research diagnostics, not source identifiers",
    }
