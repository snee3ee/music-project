import json
import struct
from dataclasses import asdict, replace

import pytest
from dsd_fixtures import dff, dsf, dsf_metadata
from mutagen.dsf import DSF

from music_project.core.analysis import analyze
from music_project.core.dsd_container import DSDContainer, inspect_dsd
from music_project.core.duration import select_dsd_duration, with_duration
from music_project.core.library import Library
from music_project.core.models import AudioInfo
from music_project.core.probe import probe


@pytest.mark.parametrize("padding", [0, 100000, 500000])
@pytest.mark.parametrize("artwork", [False, True])
def test_actual_ffprobe_metadata_estimate_does_not_change_audio_duration(
    tmp_path, settings, padding, artwork
):
    path = dsf(tmp_path / "generated.dsf", seconds=0.15)
    base = probe(path, settings)
    before = path.stat().st_size
    dsf_metadata(path, padding_bytes=padding, artwork=artwork)
    after = probe(path, settings)
    assert after.duration == base.duration == 0.15
    assert after.duration_status == "Derived"
    assert after.duration_source == "DSF sample count / native rate"
    assert DSF(path).info.length == after.duration
    added = path.stat().st_size - before
    nominal_bytes_per_second = after.sample_rate * after.channels / 8
    # Metamorphic backend check: only ID3 changed; bitrate estimate includes those bytes.
    assert after.ffprobe_duration - base.ffprobe_duration == pytest.approx(
        added / nominal_bytes_per_second, abs=1.1e-6
    )
    assert after.ffprobe_duration > after.duration
    result, context = analyze(path, replace(settings, dsd_mode="full"))
    assert context is None and result.scope["complete_file"]
    assert result.info.duration == 0.15 and result.info.duration_status == "Verified"
    assert result.info.ffprobe_duration == after.ffprobe_duration
    assert result.info.duration_details["consistency"] == "Passed"
    assert result.findings["dsd"].measurements["ffprobe_duration_seconds"] == after.ffprobe_duration
    json.dumps(result.to_dict(), allow_nan=False)


def test_exact_dsf_padding_and_metadata_boundaries(tmp_path, settings):
    rate = 11289600
    path = dsf_metadata(dsf(tmp_path / "generated.dsf", rate=rate, seconds=0.15))
    info = probe(path, settings)
    structure = inspect_dsd(info)
    assert structure.status == "Passed"
    assert structure.metadata_offset == structure.audio_data_end
    assert structure.metadata_bytes == path.stat().st_size - structure.metadata_offset
    assert structure.metadata_type == "ID3v2.3"
    assert structure.audio_data_offset == 92
    valid_bytes = (structure.samples_per_channel + 7) // 8 * info.channels
    assert structure.valid_packed_audio_bytes == valid_bytes
    assert structure.padding_bytes == structure.payload_bytes - valid_bytes
    assert (
        structure.padding_tolerance_seconds
        == (structure.payload_bytes * 8 // info.channels - structure.samples_per_channel) / rate
    )
    assert structure.padding_tolerance_seconds < 4096 * 8 / rate


def test_dff_duration_uses_only_uncompressed_audio_chunk(tmp_path, settings):
    path = dff(tmp_path / "generated.dff")
    base = probe(path, settings)
    original = bytearray(path.read_bytes())
    metadata = b"JUNK" + struct.pack(">Q", 100000) + b"\0" * 100000
    struct.pack_into(">Q", original, 4, len(original) + len(metadata) - 12)
    path.write_bytes(original + metadata)
    info = probe(path, settings)
    assert info.duration == base.duration == 0.15
    assert info.duration_source == "DFF payload length / channels / native rate"
    result, _ = analyze(path, replace(settings, dsd_mode="full"))
    assert result.info.duration_status == "Verified" and result.info.duration == 0.15


@pytest.mark.parametrize(
    "seconds,source_status,decode_status,eof,status",
    [
        (3, "Passed", "Partial", False, "Derived"),
        (10, "Passed", "Passed", True, "Verified"),
        (10, "Passed", "Failed", False, "Derived"),
        (10.1, "Passed", "Failed", True, "Ambiguous"),
        (9.9, "Passed", "Passed", True, "Ambiguous"),
        (10, "Failed", "Passed", True, "Unknown"),
        (10, "Unsupported", "Unsupported", False, "Unsupported"),
    ],
)
def test_duration_selection_scope_and_disagreement(
    info, seconds, source_status, decode_status, eof, status
):
    structure = DSDContainer(
        status=source_status, container="DSF", rate=1000000, samples_per_channel=10000000
    )
    result = select_dsd_duration(
        info,
        structure,
        decoded_seconds=seconds,
        full_decode_reached_eof=eof,
        decode_status=decode_status,
        pcm_rate=352800,
    )
    assert result.status == status
    assert result.seconds == (10 if status in {"Verified", "Derived"} else None)
    if not eof:
        assert result.decoded_minus_container_seconds is None


def test_exact_padding_tolerance_does_not_allow_arbitrary_extra_duration(info):
    structure = DSDContainer(
        status="Passed",
        container="DSF",
        rate=11289600,
        samples_per_channel=11289600 * 10,
        padding_tolerance_seconds=0.001,
    )
    common = {"full_decode_reached_eof": True, "decode_status": "Passed", "pcm_rate": 352800}
    assert (
        select_dsd_duration(info, structure, decoded_seconds=10.001, **common).status == "Verified"
    )
    assert (
        select_dsd_duration(info, structure, decoded_seconds=10.002, **common).status == "Ambiguous"
    )


def test_probe_does_not_promote_estimate_from_invalid_dsf(tmp_path, settings):
    path = dsf(tmp_path / "generated.dsf")
    data = bytearray(path.read_bytes())
    struct.pack_into("<Q", data, 12, len(data) + 100)
    path.write_bytes(data)
    info = probe(path, settings)
    assert info.ffprobe_duration is not None
    assert info.duration is None and info.duration_status == "Unknown"


def test_unknown_dst_and_legacy_record_serialization(info):
    old = asdict(info)
    for field in ("ffprobe_duration", "duration_source", "duration_status", "duration_details"):
        old.pop(field)
    legacy = AudioInfo(**old)
    structure = DSDContainer(status="Unsupported", container="DFF", compression="DST")
    selection = select_dsd_duration(legacy, structure)
    selected = with_duration(legacy, selection)
    assert selected.duration is None and selected.ffprobe_duration == legacy.duration
    assert selected.duration_status == "Unsupported"
    assert AudioInfo(**asdict(selected)) == selected


def test_library_uses_audio_duration_with_secondary_estimate(tmp_path, settings):
    root = tmp_path / "audio"
    root.mkdir()
    dsf_metadata(dsf(root / "generated.dsf"), padding_bytes=500000)
    library = Library(tmp_path / "library.sqlite3")
    assert library.scan(root, settings, audio_hash=False)["errors"] == 0
    row = library.records()[0]
    assert row["info"]["duration"] == 0.15
    assert (
        row["info"]["duration_status"] == "Derived"
    )  # Null decode has no counted PCM corroboration.
    assert row["info"]["ffprobe_duration"] > row["info"]["duration"]


@pytest.mark.parametrize("invalid", [float("nan"), float("inf"), -1.0])
def test_invalid_decoded_duration_is_not_serialized_as_measurement(info, invalid):
    structure = DSDContainer(
        status="Passed", container="DSF", rate=1000000, samples_per_channel=10000000
    )
    result = select_dsd_duration(
        info,
        structure,
        decoded_seconds=invalid,
        full_decode_reached_eof=True,
        decode_status="Passed",
        pcm_rate=352800,
    )
    assert (
        result.status == "Ambiguous" and result.seconds is None and result.decoded_seconds is None
    )
    json.dumps(asdict(result), allow_nan=False)
