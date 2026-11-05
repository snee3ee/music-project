import struct
import sys
from dataclasses import replace

import pytest

from music_project.core.analysis import analyze
from music_project.core.config import Settings
from music_project.core.decoder import PCMContext
from music_project.core.devices import DeviceProfile, compatibility
from music_project.core.disc import inspect_iso, parse_cue, sacd_command
from music_project.core.models import AudioError
from music_project.core.probe import probe


def test_cue_metadata_and_boundaries(tone, tmp_path):
    cue = tmp_path / "album.cue"
    cue.write_text(
        f'TITLE "Альбом"\nPERFORMER "Артист"\nFILE "{tone.name}" WAVE\n'
        'TRACK 01 AUDIO\nTITLE "Первый"\nINDEX 01 00:00:00\n'
        "TRACK 02 AUDIO\nINDEX 00 00:01:00\nINDEX 01 00:02:37\n",
        encoding="utf-8",
    )
    result = parse_cue(cue)
    assert not result["issues"]
    assert result["tracks"][1]["indexes"]["01"] == 187
    assert result["metadata"]["title"] == "Альбом"


@pytest.mark.parametrize("reference", ["missing.flac", "../outside.flac", "C:/private.flac"])
def test_cue_bad_reference(tmp_path, reference):
    cue = tmp_path / "bad.cue"
    cue.write_text(f'FILE "{reference}" WAVE\nTRACK 01 AUDIO\nINDEX 01 00:61:00', encoding="utf-8")
    assert len(parse_cue(cue)["issues"]) >= 2
    with pytest.raises(AudioError, match="специализированного"):
        probe(cue)


def test_iso_signature_missing_backend_and_plan(tmp_path):
    iso = tmp_path / "disc.iso"
    with iso.open("wb") as stream:
        stream.seek(510 * 2048)
        stream.write(b"SACDMTOC")
    missing = Settings(sacd_extract="not-installed-sacd-extract")
    result = inspect_iso(iso, missing)
    assert result["type"] == "SACD signature detected"
    assert "Backend unavailable" in result["backend"]
    with pytest.raises(AudioError, match="Backend unavailable"):
        sacd_command(iso, tmp_path / "output", [1], settings=missing)
    configured = replace(missing, sacd_extract=sys.executable)
    command = sacd_command(iso, tmp_path / "output", [3, 1, 3], settings=configured)
    assert command[1:7] == ["-2", "-s", "-c", "-t", "1,3", "-i"]
    assert str(iso.resolve()) in command
    with pytest.raises(AudioError):
        sacd_command(iso, tmp_path, [0], settings=configured)


def test_iso_unknown_not_called_sacd(tmp_path):
    iso = tmp_path / "ordinary.iso"
    iso.write_bytes(b"arbitrary content")
    assert inspect_iso(iso)["type"] == "Unknown disc image"


def make_dsf(path):
    channels, rate, block = 2, 2822400, 4096
    data = b"\x69" * (block * channels)
    fmt = b"fmt " + struct.pack("<QIIIIIIQII", 52, 1, 0, 2, channels, rate, 1, block * 8, block, 0)
    total = 28 + len(fmt) + 12 + len(data)
    path.write_bytes(
        b"DSD "
        + struct.pack("<QQQ", 28, total, 0)
        + fmt
        + b"data"
        + struct.pack("<Q", 12 + len(data))
        + data
    )
    return path


def make_dff(path):
    def chunk(name, data):
        return name + struct.pack(">Q", len(data)) + data + (b"\0" if len(data) % 2 else b"")

    props = (
        b"SND "
        + chunk(b"FS  ", struct.pack(">I", 2822400))
        + chunk(b"CHNL", struct.pack(">H", 2) + b"SLFTSRGT")
        + chunk(b"CMPR", b"DSD " + bytes([0]))
    )
    body = (
        b"DSD "
        + chunk(b"FVER", bytes([1, 5, 0, 0]))
        + chunk(b"PROP", props)
        + chunk(b"DSD ", b"\x69" * 8192)
    )
    path.write_bytes(b"FRM8" + struct.pack(">Q", len(body)) + body)
    return path


@pytest.mark.parametrize("extension,writer", [("dsf", make_dsf), ("dff", make_dff)])
def test_dsd_synthetic_container_routing(tmp_path, settings, extension, writer):
    path = writer(tmp_path / f"synthetic.{extension}")
    info = probe(path, settings)
    assert info.kind == "DSD"
    assert info.sample_rate == 2822400
    assert info.bit_depth is None
    result, context = analyze(path, settings)
    assert context is None and "dsd" in result.findings
    assert "dsd_integrity" in result.findings
    assert result.findings["dsd"].measurements["dsd_family"] == "DSD64"
    with pytest.raises(AudioError, match="Native DSD"):
        PCMContext.load(info)


def test_device_constraints(info):
    profile = DeviceProfile("Test", ("pcm_s24le",), 96000, (24,), 2)
    assert compatibility(info, profile).status == "Compatible"
    assert compatibility(replace(info, sample_rate=192000), profile).status == "Incompatible"
    assert compatibility(replace(info, sample_rate=0), profile).status == "Unknown"
    assert (
        compatibility(replace(info, kind="DSD", codec="dsd_lsbf_planar"), profile).status
        == "Incompatible"
    )


@pytest.mark.skip(reason="No real SACD fixture or sacd_extract backend; end-to-end unverified")
def test_real_sacd_integration():
    pass
