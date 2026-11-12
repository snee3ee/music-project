"""Independent RFC9639 verbatim frames: known signed PCM and embedded checksums.

No product packing, encoder or digest verifier is used to generate these fixtures.
Only byte-aligned integer depths and <=127 fixed-size blocks are needed here.
"""

import hashlib

import numpy as np


def crc(data, width, polynomial):
    result = 0
    for byte in data:
        result ^= byte << (width - 8)
        for _ in range(8):
            result = ((result << 1) ^ (polynomial if result & (1 << (width - 1)) else 0)) & (
                (1 << width) - 1
            )
    return result.to_bytes(width // 8, "big")


def verbatim_flac(path, values, bits, rate=48000):
    values = np.asarray(values)
    frames, channels = values.shape
    assert bits in (8, 16, 24, 32) and channels in (1, 2)
    assert frames % 4096 == 0 and frames // 4096 < 128 and rate == 48000

    def packed(array, order):
        return b"".join(int(value).to_bytes(bits // 8, order, signed=True) for value in array.flat)

    native_pcm = packed(values, "little")
    md5 = hashlib.md5(native_pcm, usedforsecurity=False).digest()
    packed_info = (rate << 44) | ((channels - 1) << 41) | ((bits - 1) << 36) | frames
    stream_info = (4096).to_bytes(2, "big") * 2 + bytes(6) + packed_info.to_bytes(8, "big") + md5
    with path.open("wb") as out:
        out.write(b"fLaC\x80\0\0\x22" + stream_info)
        for number, first in enumerate(range(0, frames, 4096)):
            # fixed block4096, 48kHz; stream-info bit depth code for32.
            depth_code = {8: 1, 16: 4, 24: 6, 32: 0}[bits]
            header = bytes([255, 248, 202, ((channels - 1) << 4) | (depth_code << 1), number])
            block = header + crc(header, 8, 0x07)
            for channel in values[first : first + 4096].T:
                block += b"\x02" + packed(channel, "big")
            out.write(block + crc(block, 16, 0x8005))
    return path, native_pcm
