"""Native-FLAC STREAMINFO MD5 comparison, independent of decoder CRC warnings."""

import hashlib
from pathlib import Path

import numpy as np


class FlacMD5:
    def __init__(self, info):
        self.digest = hashlib.md5(usedforsecurity=False)
        self.status = "Not applicable"
        self.reason = "Not native FLAC"
        self.expected = None
        self.bits = None
        self.samples = 0
        self.expected_samples = None
        if info.codec != "flac":
            return
        with Path(info.path).open("rb") as source:
            header = source.read(42)
        if (
            len(header) != 42
            or header[:4] != b"fLaC"
            or header[4] & 127
            or int.from_bytes(header[5:8], "big") != 34
        ):
            self.status = "Unsupported"
            self.reason = "Native FLAC STREAMINFO not accessible"
            return
        packed = int.from_bytes(header[18:26], "big")
        rate = packed >> 44
        channels = ((packed >> 41) & 7) + 1
        bits = ((packed >> 36) & 31) + 1
        self.expected_samples = packed & ((1 << 36) - 1)
        self.expected = header[26:42].hex()
        self.bits = bits
        if (rate, channels, bits) != (
            info.sample_rate,
            info.channels,
            info.bit_depth,
        ):
            self.status = "Unsupported"
            self.reason = "STREAMINFO properties inconsistent with probed stream"
            return
        if bits not in (8, 16, 24, 32):
            self.status = "Not validated"
            self.reason = (
                f"Native {bits}-bit FLAC MD5 path not validated; tested depths are8/16/24/32"
            )
            return
        if self.expected == "0" * 32:
            self.status = "Unknown"
            self.reason = "STREAMINFO provides no MD5 digest"
            return
        self.status = "Pending"
        self.reason = "Requires complete native decoded PCM"

    def consume(self, x):
        self.samples += len(x)
        if self.status != "Pending":
            return
        integers = np.rint(x * (2 ** (self.bits - 1))).astype("<i4")
        encoded = (
            integers.astype("<i4")
            .view(np.uint8)
            .reshape(-1, 4)[:, : self.bits // 8]
            .copy()
            .tobytes()
        )
        self.digest.update(encoded)

    def result(self, complete):
        calculated = self.digest.hexdigest() if self.status == "Pending" else None
        status = self.status
        if status == "Pending":
            status = (
                "Verified"
                if complete and self.expected == calculated
                else "Failed"
                if complete
                else "Partial"
            )
        md5_status = status
        count_status = (
            ("Verified" if self.samples == self.expected_samples else "Failed")
            if complete and self.expected_samples
            else "Partial"
            if not complete and self.expected_samples
            else "Unknown"
        )
        if count_status == "Failed":
            status = "Failed"
        reason = (
            "Embedded MD5 matched after complete native PCM decoding"
            if status == "Verified"
            else "Embedded digest or declared frame count does not match decoded PCM"
            if status == "Failed"
            else self.reason
        )
        return {
            "status": status,
            "md5_status": md5_status,
            "frame_count_status": count_status,
            "reason": reason,
            "expected_md5": self.expected,
            "calculated_md5": calculated,
            "expected_frames": self.expected_samples,
            "decoded_frames": self.samples,
            "method": "RFC9639 STREAMINFO MD5 of signed interleaved little-endian native PCM; no resampling/gain",
            "limitation": "Matches the embedded digest, not an authenticated external archive; zero digest is not verification",
        }
