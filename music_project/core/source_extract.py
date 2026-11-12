"""Bounded selected-track representations; originals are always opened read-only."""

import math
import shutil
import struct
from pathlib import Path

import numpy as np

from music_project.core.decoder import input_args
from music_project.core.dsd_container import inspect_dsd
from music_project.core.models import AudioError
from music_project.core.subprocess_utils import run


def ensure_track_space(folder: Path, estimated_bytes: int, settings):
    if (
        estimated_bytes > settings.max_track_bytes
        or estimated_bytes > shutil.disk_usage(folder).free - 16 * 1024**2
    ):
        raise AudioError("Insufficient temporary disk budget for the selected track")


def native_track(info, first: int, last: int, target: Path, *, cancelled=None):
    structure = inspect_dsd(info)
    if (
        structure.status != "Passed"
        or structure.compression != "DSD"
        or info.channels not in (1, 2)
    ):
        raise AudioError(
            "Unsupported: native CUE extraction requires validated mono/stereo uncompressed DSF/DFF; DST is not decoded by this reader"
        )
    if first % 8 or not 0 <= first < last <= structure.samples_per_channel:
        raise AudioError("Unsupported/non-byte-aligned native DSD interval")
    channels, count = info.channels, last - first
    payload = math.ceil(count / 32768) * 4096 * channels
    reverse = np.array([int(f"{x:08b}"[::-1], 2) for x in range(256)], dtype=np.uint8)
    with open(info.path, "rb") as src, target.open("xb") as dst:
        dst.write(b"DSD " + struct.pack("<QQQ", 28, 92 + payload, 0))
        dst.write(
            b"fmt "
            + struct.pack(
                "<QIIIIIIQII", 52, 1, 0, channels, channels, info.sample_rate, 1, count, 4096, 0
            )
        )
        dst.write(b"data" + struct.pack("<Q", 12 + payload))
        remaining = math.ceil(count / 8)
        byte_offset = first // 8
        while remaining:
            if cancelled and cancelled():
                raise AudioError("Cancelled: native selected-track copy")
            n = min(4096, remaining)
            output = np.full((channels, 4096), 0x69, dtype=np.uint8)
            if structure.container == "DFF":
                src.seek(structure.audio_data_offset + byte_offset * channels)
                b = src.read(n * channels)
                if len(b) != n * channels:
                    raise AudioError("Truncated native DFF during selected-track read")
                output[:, :n] = reverse[np.frombuffer(b, dtype=np.uint8).reshape(n, channels).T]
            else:
                filled = 0
                while filled < n:
                    group, within = divmod(byte_offset + filled, 4096)
                    size = min(n - filled, 4096 - within)
                    for ch in range(channels):
                        src.seek(
                            structure.audio_data_offset + (group * channels + ch) * 4096 + within
                        )
                        b = src.read(size)
                        if len(b) != size:
                            raise AudioError("Truncated native DSF during selected-track read")
                        raw = np.frombuffer(b, dtype=np.uint8)
                        output[ch, filled : filled + size] = (
                            reverse[raw] if structure.bit_order == "big" else raw
                        )
                    filled += size
            dst.write(output.tobytes())
            byte_offset += n
            remaining -= n
    return {
        "method": "Native packed DSD copy to DSF; bit order normalized, no PCM conversion",
        "first_native_frame": first,
        "last_native_frame_exclusive": last,
        "native_frames": count,
        "temporary_bytes": target.stat().st_size,
    }


def prepare_cue_track(source, info, folder: Path, settings, *, cancelled=None):
    rate = info.sample_rate
    first = (source.start_75 * rate + 74) // 75
    last = (
        (source.end_75 * rate + 74) // 75
        if source.end_75 is not None
        else round(info.duration * rate)
    )
    if not 0 <= first < last:
        raise AudioError("Invalid selected-track frame range")
    if info.kind == "DSD":
        target = folder / "selected-track.dsf"
        ensure_track_space(
            folder, 92 + math.ceil((last - first) / 32768) * 4096 * info.channels, settings
        )
        return target, native_track(info, first, last, target, cancelled=cancelled)
    if info.kind != "PCM" or not info.lossless:
        raise AudioError(
            "Unsupported: CUE selected-track precision is validated only for lossless PCM and native DSD"
        )
    if info.codec.startswith("pcm_f"):
        codec = "pcm_f64le"
    elif info.bit_depth in (8, 16, 24, 32):
        codec = "pcm_u8" if info.bit_depth == 8 else f"pcm_s{info.bit_depth}le"
    else:
        raise AudioError("Unsupported: native PCM bit depth is unknown")
    target = folder / "selected-track.wav"
    ensure_track_space(folder, (last - first) * info.channels * 8 + 65536, settings)
    command = input_args(info, settings)
    seek = max(0, first // rate - 1)
    if seek:
        index = command.index("-i")
        command[index:index] = ["-ss", str(seek)]
    offset = seek * rate
    command += [
        "-af",
        f"atrim=start_sample={first - offset}:end_sample={last - offset},asetpts=PTS-STARTPTS",
        "-t",
        f"{(last - first) / rate:.12f}",
        "-c:a",
        codec,
        "-rf64",
        "auto",
        "-n",
        str(target),
    ]
    result = run(command, timeout=settings.timeout, cancelled=cancelled)
    return target, {
        "method": "Native-rate/channel PCM decode and exact sample trim; lossless temporary WAV",
        "first_native_frame": first,
        "last_native_frame_exclusive": last,
        "native_frames": last - first,
        "command": command,
        "warnings": result.stderr,
        "temporary_bytes": target.stat().st_size,
    }
