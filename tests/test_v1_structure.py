"""Adversarial generated DSDIFF chunks; original recordings are never mutated."""

import struct

import pytest

from music_project.core.dsd_container import inspect_dsd
from music_project.core.models import AudioInfo


def chunk(tag, body):
    return tag + struct.pack(">Q", len(body)) + body + b"\0" * (len(body) % 2)


def dff_parts():
    return {
        "version": chunk(b"FVER", bytes([1, 5, 0, 0])),
        "properties": chunk(
            b"PROP",
            b"SND "
            + chunk(b"FS  ", struct.pack(">I", 2822400))
            + chunk(b"CHNL", struct.pack(">H", 2) + b"SLFTSRGT")
            + chunk(b"CMPR", b"DSD \x00"),
        ),
        "audio": chunk(b"DSD ", b"\x69\x96" * 4096),
    }


def inspect_parts(tmp_path, parts):
    body = b"DSD " + b"".join(parts)
    path = tmp_path / "generated.dff"
    path.write_bytes(b"FRM8" + struct.pack(">Q", len(body)) + body)
    info = AudioInfo(
        str(path),
        "dff",
        "dsd_msbf",
        "DSD",
        2822400,
        2,
        "stereo",
        None,
        None,
        path.stat().st_size,
        None,
        False,
    )
    return inspect_dsd(info)


@pytest.mark.parametrize(
    "case",
    [
        "missing-version",
        "duplicate-version",
        "late-version",
        "short-version",
        "late-properties",
        "truncated-name",
        "short-sound-property",
    ],
)
def test_dff_required_chunks_order_and_field_bounds(tmp_path, case):
    p = dff_parts()
    parts = list(p.values())
    if case == "missing-version":
        parts = parts[1:]
    elif case == "duplicate-version":
        parts.insert(1, p["version"])
    elif case == "late-version":
        parts = [p["properties"], p["version"], p["audio"]]
    elif case == "short-version":
        parts[0] = chunk(b"FVER", b"\x01")
    elif case == "late-properties":
        parts = [p["version"], p["audio"], p["properties"]]
    elif case == "truncated-name":
        raw = p["properties"].replace(b"DSD \x00", b"DSD \xff")
        parts[1] = raw
    else:
        parts.insert(1, chunk(b"PROP", b"SN"))
    result = inspect_parts(tmp_path, parts)
    assert result.status == "Failed", (case, result)
    assert result.errors


def test_dff_unknown_major_version_is_unsupported(tmp_path):
    p = dff_parts()
    p["version"] = chunk(b"FVER", bytes([2, 0, 0, 0]))
    assert inspect_parts(tmp_path, p.values()).status == "Unsupported"


def test_dff_unknown_chunks_and_names_with_odd_padding_are_preserved(tmp_path):
    p = dff_parts()
    # Same major version, unknown extension chunks and a valid counted name.
    p["version"] = chunk(b"FVER", bytes([1, 6, 0, 0]))
    props = p["properties"][12:]
    props = props.replace(chunk(b"CMPR", b"DSD \0"), chunk(b"CMPR", b"DSD \x04test"))
    p["properties"] = chunk(b"PROP", props)
    result = inspect_parts(
        tmp_path, [p["version"], chunk(b"TEST", b"abc"), p["properties"], p["audio"]]
    )
    assert result.status == "Passed", result
    assert result.duration == pytest.approx(4096 * 8 / 2822400)
