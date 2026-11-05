"""Generated containers only; never recordings or claims about historical provenance."""

import struct
from io import BytesIO

import numpy as np
from mutagen.id3 import APIC, ID3, TIT2
from PIL import Image


def dsf(path, rate=11289600, seconds=0.15, channels=2, samples=None, bit_order=1):
    count = int(rate * seconds) if samples is None else len(samples)
    block = 4096
    channel_bytes = (count + 7) // 8
    blocks = (channel_bytes + block - 1) // block
    payload_bytes = blocks * block * channels
    total = 92 + payload_bytes
    fmt = b"fmt " + struct.pack(
        "<QIIIIIIQII",
        52,
        1,
        0,
        1 if channels == 1 else 2,
        channels,
        rate,
        bit_order,
        count,
        block,
        0,
    )
    encoded = None
    if samples is not None:
        # First-order pulse-density control: cumulative desired duty, no provenance inference.
        encoded = []
        for channel in np.asarray(samples).T:
            duty = np.cumsum((channel + 1) / 2)
            bits = np.diff(np.floor(np.r_[0.0, duty])).astype(np.uint8)
            packed = np.packbits(bits, bitorder="little" if bit_order == 1 else "big").tobytes()
            encoded.append(packed.ljust(blocks * block, b"\x69"))
    with path.open("wb") as out:
        out.write(b"DSD " + struct.pack("<QQQ", 28, total, 0) + fmt)
        out.write(b"data" + struct.pack("<Q", 12 + payload_bytes))
        for index in range(blocks):
            for channel in range(channels):
                out.write(
                    encoded[channel][index * block : (index + 1) * block]
                    if encoded
                    else b"\x69" * block
                )
    return path


def dff(path, rate=2822400, seconds=0.15, compression=b"DSD "):
    def chunk(name, data):
        return name + struct.pack(">Q", len(data)) + data + (b"\0" if len(data) % 2 else b"")

    props = (
        b"SND "
        + chunk(b"FS  ", struct.pack(">I", rate))
        + chunk(b"CHNL", struct.pack(">H", 2) + b"SLFTSRGT")
        + chunk(b"CMPR", compression + b"\0")
    )
    body = (
        b"DSD "
        + chunk(b"FVER", bytes([1, 5, 0, 0]))
        + chunk(b"PROP", props)
        + chunk(compression, b"\x69" * (int(rate * seconds) // 8 * 2))
    )
    path.write_bytes(b"FRM8" + struct.pack(">Q", len(body)) + body)
    return path


def dsf_metadata(path, padding_bytes=100000, artwork=True):
    """Append generated ID3 only to a synthetic fixture, updating size and pointer."""
    tag = ID3()
    tag.add(TIT2(encoding=3, text=["Generated duration fixture"]))
    if artwork:
        picture = BytesIO()
        Image.new("RGB", (32, 32), color=(60, 90, 120)).save(picture, format="JPEG")
        tag.add(
            APIC(encoding=3, mime="image/jpeg", type=3, desc="Generated", data=picture.getvalue())
        )
    encoded = BytesIO()
    tag.save(encoded, v2_version=3, padding=lambda _: padding_bytes)
    original = bytearray(path.read_bytes())
    pointer = len(original)
    metadata = encoded.getvalue()
    struct.pack_into("<Q", original, 12, len(original) + len(metadata))
    struct.pack_into("<Q", original, 20, pointer)
    path.write_bytes(original + metadata)
    return path
