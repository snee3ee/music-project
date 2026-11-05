"""Measured FFmpeg response to generated one-bit controls. Never uses user audio."""

import hashlib
import json
import math
import struct
import tempfile
from pathlib import Path

import numpy as np

from music_project.core.config import Settings
from music_project.core.dsd_decoder import RESAMPLE, convert_window
from music_project.core.models import AudioError
from music_project.core.probe import probe

CALIBRATION_VERSION = "dsd-response-2026.11-v1"
CANDIDATES = (22050, 24000, 44100, 48000, 88200, 96000)
CONTROL_FREQUENCIES = sorted(
    {
        1000,
        *range(20000, 160001, 10000),
        *(f + delta for f in CANDIDATES for delta in (-2000, 0, 2000)),
    }
)
SEGMENT_SECONDS = 0.12
GUARD_SECONDS = 0.04


def generate_controls(path: Path, rate: int, frequencies=CONTROL_FREQUENCIES) -> list[float]:
    """First-order pulse-density accumulator; actual input fundamental measured below."""
    per_tone = round(rate * SEGMENT_SECONDS)
    if per_tone % 8:
        raise AudioError("Calibration requires byte-aligned tone durations")
    count = per_tone * len(frequencies)
    payload = math.ceil(count / 32768) * 4096
    amplitudes = []
    with path.open("wb") as out:
        out.write(b"DSD " + struct.pack("<QQQ", 28, 92 + payload, 0))
        out.write(b"fmt " + struct.pack("<QIIIIIIQII", 52, 1, 0, 1, 1, rate, 1, count, 4096, 0))
        out.write(b"data" + struct.pack("<Q", 12 + payload))
        written = 0
        for frequency in frequencies:
            carry = 0.0
            previous_floor = 0.0
            phasor = 0j
            measured = 0
            for first in range(0, per_tone, 65536):
                indices = np.arange(first, min(per_tone, first + 65536))
                phase = 2 * np.pi * frequency * indices / rate
                desired = 0.1 * np.sin(phase)
                accumulated = np.cumsum((desired + 1) / 2) + carry
                floors = np.floor(accumulated)
                bits = np.diff(np.r_[previous_floor, floors]).astype(np.uint8)
                carry, previous_floor = float(accumulated[-1]), float(floors[-1])
                encoded = np.packbits(bits, bitorder="little").tobytes()
                out.write(encoded)
                written += len(encoded)
                use = indices >= round(GUARD_SECONDS * rate)
                signs = bits[use].astype(np.float64) * 2 - 1
                phasor += np.sum(signs * np.exp(-1j * phase[use]))
                measured += int(use.sum())
            amplitudes.append(float(2 * abs(phasor) / measured))
        out.write(b"\x69" * (payload - written))
    return amplitudes


def response_key(native_rate: int, settings: Settings, version: str) -> str:
    executable = Path(settings.require("ffmpeg"))
    stat = executable.stat()
    value = {
        "native_rate": native_rate,
        "output_rate": settings.dsd_pcm_rate,
        "ffmpeg": str(executable),
        "size": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
        "version": version,
        "resample": RESAMPLE,
        "method": CALIBRATION_VERSION,
    }
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def calibrate_response(
    native_rate: int, settings: Settings, version: str, *, cancelled=None
) -> dict:
    if native_rate not in (2822400, 5644800, 11289600, 22579200):
        return {
            "status": "Unsupported",
            "reason": "Native rate outside calibrated DSD64/128/256/512 family",
        }
    key = response_key(native_rate, settings, version)
    cache = Path(settings.origin_cache_dir)
    cache.mkdir(parents=True, exist_ok=True)
    target = cache / f"{key}.json"
    if target.is_file():
        try:
            previous = json.loads(target.read_text(encoding="utf-8"))
            if (
                previous.get("key") == key
                and previous.get("status") == "Measured"
                and len(previous["controls"]) == len(CONTROL_FREQUENCIES)
                and [r["frequency_hz"] for r in previous["controls"]] == CONTROL_FREQUENCIES
                and previous["output_header"]["sample_rate_hz"] == settings.dsd_pcm_rate
                and previous["controls"][0]["output_amplitude"] > 0.001
            ):
                return previous
        except (OSError, ValueError, KeyError, TypeError):
            pass
    with tempfile.TemporaryDirectory(prefix="generated-controls-", dir=cache) as temporary:
        path = Path(temporary) / "generated.dsf"
        inputs = generate_controls(path, native_rate)
        info = probe(path, settings)
        rate = settings.dsd_pcm_rate
        frames_per_tone = round(SEGMENT_SECONDS * rate)
        guard = round(GUARD_SECONDS * rate)
        phasors = np.zeros(len(inputs), dtype=np.complex128)
        aliases = np.zeros(len(inputs), dtype=np.complex128)
        energy = np.zeros(len(inputs))
        counts = np.zeros(len(inputs), dtype=np.int64)
        halves = np.zeros((len(inputs), 2), dtype=np.complex128)
        half_counts = np.zeros((len(inputs), 2), dtype=np.int64)
        received = 0

        def consume(samples):
            nonlocal received
            first = 0
            while first < len(samples):
                tone = received // frames_per_tone
                if tone >= len(inputs):
                    received += len(samples) - first
                    break
                local = received % frames_per_tone
                take = min(len(samples) - first, frames_per_tone - local)
                indices = np.arange(local, local + take)
                selected = indices >= guard
                x = samples[first : first + take, 0][selected].astype(float)
                time = indices[selected] / rate
                frequency = CONTROL_FREQUENCIES[tone]
                folded = abs((frequency + rate / 2) % rate - rate / 2)
                wave = np.exp(-2j * np.pi * frequency * time)
                phasors[tone] += np.sum(x * wave)
                aliases[tone] += np.sum(x * np.exp(-2j * np.pi * folded * time))
                energy[tone] += np.sum(x * x)
                counts[tone] += len(x)
                for half in (0, 1):
                    mask = (indices[selected] < (guard + frames_per_tone) // 2) == (half == 0)
                    halves[tone, half] += np.sum(x[mask] * wave[mask])
                    half_counts[tone, half] += int(mask.sum())
                first += take
                received += take

        attempt = convert_window(info, settings, 0, None, consume, cancelled=cancelled)
        if attempt.status != "Passed" or np.any(counts == 0):
            raise AudioError("Calibration conversion failed: " + str(attempt.fatal_error))
        rows = []
        for i, frequency in enumerate(CONTROL_FREQUENCIES):
            output = float(2 * abs(phasors[i]) / counts[i])
            half_amplitudes = 2 * np.abs(halves[i]) / np.maximum(half_counts[i], 1)
            stability = float(
                abs(20 * np.log10(max(half_amplitudes[0], 1e-30) / max(half_amplitudes[1], 1e-30)))
            )
            gain = float(20 * np.log10(max(output, 1e-30) / inputs[i]))
            rows.append(
                {
                    "frequency_hz": frequency,
                    "input_amplitude_native_sign_units": inputs[i],
                    "output_amplitude": output,
                    "gain_db": gain,
                    "half_window_amplitude_difference_db": stability,
                    "above_output_nyquist": frequency >= rate / 2,
                    "folded_frequency_hz": abs((frequency + rate / 2) % rate - rate / 2),
                    "folded_component_db_re_input": float(
                        20 * np.log10(max(2 * abs(aliases[i]) / counts[i], 1e-30) / inputs[i])
                    ),
                    "output_mean_square": float(energy[i] / counts[i]),
                }
            )
        reference_gain = rows[0]["gain_db"]
        if rows[0]["output_amplitude"] < 0.001:
            raise AudioError("Calibration reference tone not recovered")
        for row in rows:
            row["relative_gain_db"] = row["gain_db"] - reference_gain
            row["within_passband_tolerance"] = (
                not row["above_output_nyquist"]
                and abs(row["relative_gain_db"]) <= 0.5
                and row["half_window_amplitude_difference_db"] <= 0.5
            )
        result = {
            "status": "Measured",
            "key": key,
            "method_version": CALIBRATION_VERSION,
            "native_rate_hz": native_rate,
            "pcm_rate_hz": rate,
            "ffmpeg_version": version,
            "control": "generated first-order pulse-density tones; actual native fundamental measured",
            "segment_seconds": SEGMENT_SECONDS,
            "guard_seconds": GUARD_SECONDS,
            "reference_hz": 1000,
            "passband_tolerance_db": 0.5,
            "controls": rows,
            "command": attempt.command,
            "output_header": attempt.output_header,
            "warnings": attempt.warnings,
            "limits": "Discrete tone controls, not continuous response certification or a professional modulator model; residual includes modulation noise, not uniquely aliasing",
        }
        target.write_text(json.dumps(result, indent=2, allow_nan=False), encoding="utf-8")
        return result


def boundary_chain_valid(profile: dict, frequency: int) -> bool:
    if profile.get("status") != "Measured":
        return False
    controls = {r["frequency_hz"]: r for r in profile["controls"]}
    return all(
        controls.get(frequency + d, {}).get("within_passband_tolerance", False)
        for d in (-2000, 0, 2000)
    )


def controlled_bandwidth(profile: dict) -> float:
    """Highest consecutive passing control, stopping at first failed control."""
    highest = 0.0
    for row in profile.get("controls", []):
        if not row.get("within_passband_tolerance"):
            break
        highest = float(row["frequency_hz"])
    return highest
