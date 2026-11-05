"""Read-only, bounded structural checks. These do not validate audio decodability."""

import math
import struct
from dataclasses import dataclass, field
from pathlib import Path
from typing import BinaryIO

from music_project.core.models import AudioInfo


@dataclass
class DSDContainer:
    status: str = "Unknown"
    container: str = "Unknown"
    compression: str = "Unknown"
    rate: int = 0
    channels: int = 0
    samples_per_channel: int | None = None
    payload_bytes: int = 0
    padding_tolerance_seconds: float = 0
    declared_file_bytes: int | None = None
    audio_data_offset: int | None = None
    audio_data_end: int | None = None
    data_chunk_bytes: int | None = None
    valid_packed_audio_bytes: int | None = None
    padding_bytes: int = 0
    padding_samples_per_channel: int = 0
    metadata_offset: int | None = None
    metadata_bytes: int = 0
    metadata_type: str = "Not applicable"
    bit_order: str = "Unknown"
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def duration(self) -> float | None:
        return (
            self.samples_per_channel / self.rate if self.rate and self.samples_per_channel else None
        )


class StructureError(ValueError):
    pass


class VariantError(ValueError):
    pass


def read_exact(stream: BinaryIO, count: int) -> bytes:
    data = stream.read(count)
    if len(data) != count:
        raise StructureError("Truncated container header")
    return data


def _dsf(stream: BinaryIO, size: int, result: DSDContainer):
    result.container, result.compression = "DSF", "DSD"
    header_size, declared_size, metadata = struct.unpack("<QQQ", read_exact(stream, 24))
    result.declared_file_bytes = declared_size
    result.metadata_offset = metadata or None
    if header_size != 28:
        raise VariantError("Unsupported DSF header size")
    if declared_size != size:
        raise StructureError(f"DSF declared file size {declared_size} != actual {size}")
    if read_exact(stream, 4) != b"fmt ":
        raise StructureError("Missing DSF fmt chunk")
    chunk_size = struct.unpack("<Q", read_exact(stream, 8))[0]
    if chunk_size != 52:
        raise VariantError("Unsupported DSF fmt size")
    version, fmt, channel_type, channels, rate, bits, samples, block, reserved = struct.unpack(
        "<IIIIIIQII", read_exact(stream, 40)
    )
    result.rate, result.channels, result.samples_per_channel = rate, channels, samples
    result.bit_order = "little" if bits == 1 else "big" if bits == 8 else "Unknown"
    if version != 1 or fmt != 0 or bits not in (1, 8) or reserved:
        raise VariantError("Unsupported DSF version/format/bit order/reserved field")
    channel_types = {1: 1, 2: 2, 3: 3, 4: 4, 5: 4, 6: 5, 7: 6}
    if channels != channel_types.get(channel_type):
        raise StructureError("Contradictory DSF channel type/count")
    if not 0 < rate <= 22579200 or not samples:
        raise StructureError("Impossible DSF sample rate/count")
    if block != 4096:
        raise VariantError("DSF block size other than 4096 is not validated")
    if read_exact(stream, 4) != b"data":
        raise StructureError("Missing DSF data chunk")
    data_size = struct.unpack("<Q", read_exact(stream, 8))[0]
    if data_size < 12:
        raise StructureError("Invalid DSF data size")
    result.payload_bytes = data_size - 12
    result.data_chunk_bytes = data_size
    result.audio_data_offset = stream.tell()
    end = stream.tell() + result.payload_bytes
    result.audio_data_end = end
    required = ((samples + block * 8 - 1) // (block * 8)) * block * channels
    if end > size or result.payload_bytes != required:
        raise StructureError("Truncated or contradictory DSF padded audio payload/sample count")
    if metadata and not end <= metadata < size:
        raise StructureError("DSF metadata pointer overlaps audio or exceeds file")
    if end < size and not metadata:
        result.warnings.append("Trailing bytes outside declared DSF audio; no metadata pointer")
    result.valid_packed_audio_bytes = ((samples + 7) // 8) * channels
    result.padding_bytes = result.payload_bytes - result.valid_packed_audio_bytes
    result.padding_samples_per_channel = result.payload_bytes // channels * 8 - samples
    # Exact declared block capacity minus valid sample count, not a guessed whole-block tolerance.
    result.padding_tolerance_seconds = result.padding_samples_per_channel / rate
    if metadata:
        result.metadata_bytes = size - metadata
        stream.seek(metadata)
        header = stream.read(min(10, result.metadata_bytes))
        result.metadata_type = (
            f"ID3v2.{header[3]}" if len(header) == 10 and header[:3] == b"ID3" else "Unknown"
        )
        if result.metadata_type == "Unknown":
            result.warnings.append(
                "Metadata pointer has no complete recognized ID3 header; audio duration excludes tail"
            )


def _chunks(stream: BinaryIO, start: int, end: int):
    position = start
    count = 0
    while position < end:
        count += 1
        if count > 10000 or end - position < 12:
            raise StructureError("Invalid/excessive DFF chunk table")
        stream.seek(position)
        tag, length = struct.unpack(">4sQ", read_exact(stream, 12))
        body = position + 12
        if body + length > end:
            raise StructureError("Truncated DFF chunk")
        yield tag, body, length
        position = body + length + length % 2
        if position > end:
            raise StructureError("Missing DFF chunk padding")


def _dff(stream: BinaryIO, size: int, result: DSDContainer):
    result.container = "DFF"
    result.bit_order = "big"
    length = struct.unpack(">Q", read_exact(stream, 8))[0]
    result.declared_file_bytes = length + 12
    if length + 12 != size or read_exact(stream, 4) != b"DSD ":
        raise StructureError("Invalid/truncated DFF FRM8 size or form type")
    audio = []
    properties = set()
    for tag, body, count in _chunks(stream, 16, size):
        if tag == b"PROP":
            stream.seek(body)
            if read_exact(stream, 4) != b"SND ":
                continue
            for key, offset, n in _chunks(stream, body + 4, body + count):
                if key not in {b"FS  ", b"CHNL", b"CMPR"}:
                    continue
                if key in properties:
                    raise StructureError("Duplicate DFF sound property")
                properties.add(key)
                stream.seek(offset)
                if key == b"FS  " and n == 4:
                    result.rate = struct.unpack(">I", read_exact(stream, 4))[0]
                elif key == b"CHNL" and n >= 2:
                    result.channels = struct.unpack(">H", read_exact(stream, 2))[0]
                    if n != 2 + 4 * result.channels:
                        raise StructureError("Contradictory DFF channel identifiers/count")
                    labels = read_exact(stream, n - 2)
                    if (
                        len({labels[i : i + 4] for i in range(0, len(labels), 4)})
                        != result.channels
                    ):
                        raise StructureError("Duplicate DFF channel identifiers")
                elif key == b"CMPR" and n >= 5:
                    result.compression = (
                        read_exact(stream, 4).decode("ascii", errors="replace").strip()
                    )
        elif tag in {b"DSD ", b"DST "}:
            audio.append((tag, count, body))
    if not 0 < result.rate <= 22579200 or not 0 < result.channels <= 32 or len(audio) != 1:
        raise StructureError("Missing/impossible DFF rate/channels/audio chunk")
    tag, result.payload_bytes, result.audio_data_offset = audio[0]
    result.audio_data_end = result.audio_data_offset + result.payload_bytes
    result.data_chunk_bytes = result.payload_bytes + 12
    if tag.decode().strip() != result.compression:
        raise StructureError("Contradictory DFF compression and audio chunk")
    if result.compression == "DST":
        raise VariantError("DST compressed audio: decoding and native rate not validated")
    if result.compression != "DSD":
        raise VariantError("Unsupported DFF compression")
    if not result.payload_bytes or result.payload_bytes % result.channels:
        raise StructureError("Incomplete DFF interleaved channel frame")
    result.samples_per_channel = result.payload_bytes * 8 // result.channels
    result.valid_packed_audio_bytes = result.payload_bytes


def inspect_dsd(info: AudioInfo) -> DSDContainer:
    result = DSDContainer()
    try:
        path = Path(info.path)
        with path.open("rb") as stream:
            magic = read_exact(stream, 4)
            if magic == b"DSD ":
                _dsf(stream, path.stat().st_size, result)
            elif magic == b"FRM8":
                _dff(stream, path.stat().st_size, result)
            else:
                raise VariantError("DSD container not supported by structural validator")
        if result.rate != info.sample_rate or result.channels != info.channels:
            raise StructureError("Container rate/channels contradict ffprobe stream")
        if info.codec == "dst":
            raise StructureError("Uncompressed container contradicts DST codec")
        estimate = (
            info.ffprobe_duration
            if info.ffprobe_duration is not None
            else (info.duration if info.duration_source == "ffprobe" else None)
        )
        if estimate is not None and result.duration is not None:
            difference = estimate - result.duration
            if not math.isfinite(difference) or abs(difference) > 1e-5:
                result.warnings.append(f"ffprobe minus container duration: {difference:.9f} s")
        result.status = "Passed"
    except VariantError as exc:
        result.status = "Unsupported"
        result.warnings.append(str(exc))
    except (StructureError, OSError) as exc:
        result.status = "Failed"
        result.errors.append(str(exc))
    return result
