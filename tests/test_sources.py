"""Generated audio controls; mocked SACD protocols are not real ISO validation."""

import json
import struct
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest
from dsd_fixtures import dff, dsf

from music_project.core.config import Settings
from music_project.core.cue import cue_frames, open_cue, parse_cue, resolve_reference, track_source
from music_project.core.dsd_container import inspect_dsd
from music_project.core.dsd_native import native_blocks
from music_project.core.files import file_hash
from music_project.core.models import AudioError
from music_project.core.probe import probe
from music_project.core.sacd import backend_capabilities, iso_structure, open_sacd, parse_listing
from music_project.core.source_extract import prepare_cue_track
from music_project.core.sources import analyze_source


def cue_file(folder, names, indexes=None, encoding="utf-8"):
    path = folder / "альбом.cue"
    body = 'TITLE "Album"\nPERFORMER "Artist"\n'
    count = 1
    for name in names:
        body += f'FILE "{name}" WAVE\n'
        for position in indexes or ["00:00:00"]:
            body += f'TRACK {count:02d} AUDIO\nTITLE "Track {count}"\nINDEX 01 {position}\n'
            count += 1
    path.write_text(body, encoding=encoding)
    return path


@pytest.mark.parametrize(
    "stamp,expected", [("00:00:00", 0), ("05:07:74", 23099), ("13:03:00", 58725)]
)
def test_cue_frame_conversion(stamp, expected):
    assert cue_frames(stamp) == expected


@pytest.mark.parametrize("stamp", ["00:60:00", "00:00:75", "-1:00:00", "a:b:c", "00:1:00"])
def test_invalid_cue_frames(stamp):
    with pytest.raises(AudioError):
        cue_frames(stamp)


def test_single_and_multifile_with_real_audio_and_no_double_count(tone, tmp_path, settings):
    path = cue_file(tmp_path, [tone.name], ["00:00:00", "00:01:00", "00:02:00"])
    c = open_cue(path, settings)
    assert [t["duration_seconds"] for t in c["tracks"]] == [1, 1, 1]
    assert all(t["status"] == "Ready" for t in c["tracks"])
    other = tmp_path / "second.wav"
    other.write_bytes(tone.read_bytes())
    c = open_cue(cue_file(tmp_path, [tone.name, other.name]), settings)
    assert sum(t["duration_seconds"] for t in c["tracks"]) == 6
    assert [t["start_seconds"] for t in c["tracks"]] == [0, 0]


@pytest.mark.parametrize("encoding", ["utf-8-sig", "utf-16", "cp1251"])
def test_encoding_and_unicode_reference(tone, tmp_path, settings, encoding):
    # Western/Cyrillic fallback cannot represent Japanese; a Cyrillic file is used.
    audio = tmp_path / "звук.wav"
    audio.write_bytes(tone.read_bytes())
    c = open_cue(cue_file(tmp_path, [audio.name], encoding=encoding), settings)
    assert c["tracks"][0]["status"] == "Ready"
    assert c["encoding"] == encoding


def test_index00_pregap_policy(tone, tmp_path, settings):
    p = cue_file(tmp_path, [tone.name], ["00:00:00", "00:02:00"])
    p.write_text(
        p.read_text(encoding="utf-8").replace(
            "INDEX 01 00:02:00", "INDEX 00 00:01:00\nINDEX 01 00:02:00"
        ),
        encoding="utf-8",
    )
    c = open_cue(p, settings)
    assert [t["duration_seconds"] for t in c["tracks"]] == [2, 1]
    assert c["tracks"][1]["pregap_seconds"] == 1
    assert sum(t["duration_seconds"] for t in c["tracks"]) == 3


@pytest.mark.parametrize(
    "change",
    [
        ("INDEX 01 00:01:00", ""),
        ("INDEX 01 00:01:00", "INDEX 01 00:00:00"),
        ("INDEX 01 00:01:00", "INDEX 01 00:04:00"),
    ],
)
def test_malformed_bounds_are_not_guessed(tone, tmp_path, settings, change):
    p = cue_file(tmp_path, [tone.name], ["00:00:00", "00:01:00"])
    p.write_text(p.read_text(encoding="utf-8").replace(*change), encoding="utf-8")
    c = open_cue(p, settings)
    assert c["tracks"][0]["status"] != "Ready"


def test_external_paths_need_explicit_authorization(tmp_path, tone):
    sub = tmp_path / "inside"
    sub.mkdir()
    cue = sub / "test.cue"
    cue.write_text("", encoding="utf-8")
    assert resolve_reference(cue, "../" + tone.name)["status"] == "Authorization required"
    assert resolve_reference(cue, str(tone))["status"] == "Authorization required"
    r = resolve_reference(cue, str(tone), [tmp_path])
    assert r["status"] == "Resolved"
    for bad in ["a\0.wav", "a:stream.wav", "*name.wav"]:
        assert resolve_reference(cue, bad)["status"] != "Resolved"


def test_missing_and_unicode_ambiguous_references(tmp_path):
    cue = tmp_path / "x.cue"
    cue.write_text("", encoding="utf-8")
    assert resolve_reference(cue, "absent.flac")["status"] == "Missing"
    # Two differently normalized Unicode names remain distinct on NTFS.
    (tmp_path / "é.wav").write_bytes(b"a")
    (tmp_path / "e\u0301.wav").write_bytes(b"b")
    assert resolve_reference(cue, "É.WAV")["status"] == "Ambiguous"


def test_unsupported_construct_and_dff_wave_declaration(tmp_path, settings):
    audio = dff(tmp_path / "Steely Dan - Aja.dff", seconds=0.2)
    p = cue_file(tmp_path, [audio.name])
    c = open_cue(p, settings)
    assert c["files"][0]["declaration"] == "WAVE"
    assert c["files"][0]["audio"]["kind"] == "DSD"
    p.write_text(p.read_text(encoding="utf-8") + "PREGAP 00:01:00\n", encoding="utf-8")
    assert open_cue(p, settings)["tracks"][0]["status"] == "Unsupported"


def test_selected_pcm_samples_coverage_timestamps_and_cleanup(tmp_path, write_wav, settings):
    rate = 48000
    t = np.arange(rate) / rate
    samples = np.concatenate(
        [
            0.1 * np.sin(2 * np.pi * 1000 * t),
            0.2 * np.sin(2 * np.pi * 1000 * t),
            0.7 * np.sin(2 * np.pi * 1000 * t),
        ]
    )
    audio = write_wav(tmp_path / "source.wav", samples, bits=24)
    p = cue_file(tmp_path, [audio.name], ["00:00:00", "00:01:00", "00:02:00"])
    before = file_hash(audio)
    source = track_source(open_cue(p, settings)["tracks"][1])
    result, context = analyze_source(source, settings)
    peak = result.findings["full_peaks"].measurements
    assert peak["scope"]["frames"] == rate
    assert peak["scope"]["source_start_seconds"] == 1
    assert peak["sample_peak_dbfs"] == pytest.approx(20 * np.log10(0.2), abs=0.0001)
    assert len(context.samples) == rate and result.info.duration == 1
    assert not Path(result.info.raw["format"]["filename"]).exists()
    assert "дорожка" in next(
        c.statement for c in result.conclusions if c.conclusion_id == "integrity.decode"
    )
    assert not any(c.conclusion_id == "integrity.flac-md5" for c in result.conclusions)
    assert before == file_hash(audio)


@pytest.mark.parametrize("kind", ["dsf", "dsf-big", "dff"])
def test_native_selected_copy_preserves_bits_across_groups(tmp_path, settings, kind):
    audio = (
        dff(tmp_path / "audio.dff", seconds=0.2)
        if kind == "dff"
        else dsf(
            tmp_path / "audio.dsf",
            rate=2822400,
            seconds=0.2,
            bit_order=8 if kind == "dsf-big" else 1,
        )
    )
    p = cue_file(tmp_path, [audio.name], ["00:00:00", "00:00:03", "00:00:06"])
    source = track_source(open_cue(p, settings)["tracks"][1])
    info = probe(audio, settings)
    folder = tmp_path / "output"
    folder.mkdir()
    target, evidence = prepare_cue_track(source, info, folder, settings)
    out = probe(target, settings)
    expected = np.concatenate(list(native_blocks(info, inspect_dsd(info), 3 / 75, 3 / 75)))
    obtained = np.concatenate(list(native_blocks(out, inspect_dsd(out), 0, 3 / 75)))
    assert np.array_equal(expected, obtained)
    assert out.kind == "DSD" and out.duration == pytest.approx(0.04)
    assert evidence["method"].startswith("Native packed DSD copy")


def test_changed_reference_and_cleanup_on_engine_failure(tone, tmp_path, settings, monkeypatch):
    source = track_source(open_cue(cue_file(tmp_path, [tone.name]), settings)["tracks"][0])
    observed = []

    def fail(path, *args, **kwargs):
        observed.append(Path(path))
        assert Path(path).exists()
        raise AudioError("deliberate decoder failure")

    monkeypatch.setattr("music_project.core.analysis.analyze", fail)
    with pytest.raises(AudioError, match="deliberate"):
        analyze_source(source, settings)
    assert observed and not observed[0].parent.exists()
    tone.write_bytes(tone.read_bytes() + b"changed")
    with pytest.raises(AudioError, match="изменился"):
        source.verify()


def make_iso(path, channels=2, encoding=2):
    data = bytearray(600 * 2048)
    offset = 510 * 2048
    data[offset : offset + 10] = b"SACDMTOC\x01\x14"
    struct.pack_into(">I", data, offset + (64 if channels == 2 else 72), 544)
    struct.pack_into(">H", data, offset + (84 if channels == 2 else 86), 1)
    a = 544 * 2048
    data[a : a + 10] = (b"TWOCHTOC" if channels == 2 else b"MULCHTOC") + b"\x01\x14"
    data[a + 20] = 4
    data[a + 21] = encoding
    data[a + 32] = channels
    data[a + 69] = 1
    struct.pack_into(">2I", data, a + 72, 550, 599)
    path.write_bytes(data)
    return path


def listing(channels=2):
    return f"""sacd_extract client protocol-test
Album Information:
Title: Generated fixture
Area Information [0]:
Track Count: 1
Speaker config: {channels} Channel
Title[0]: Test track
Track_Start_Time_Code: 00:02:00 [mins:secs:frames]
Duration: 00:03:00 [mins:secs:frames]
"""


@pytest.mark.parametrize("channels,encoding,expected", [(2, 2, "DSD"), (6, 0, "DST")])
def test_sacd_structure_and_mocked_enumeration(
    tmp_path, settings, monkeypatch, channels, encoding, expected
):
    iso = make_iso(tmp_path / "generated.iso", channels, encoding)
    monkeypatch.setattr(
        "music_project.core.sacd.backend_capabilities", lambda s: {"executable": "mock-protocol"}
    )
    from music_project.core.subprocess_utils import CommandResult

    monkeypatch.setattr(
        "music_project.core.sacd.run", lambda *a, **k: CommandResult(listing(channels).encode(), "")
    )
    c = open_sacd(iso, settings)
    assert c["areas"][0]["encoding"] == expected and c["areas"][0]["channels"] == channels
    assert track_source(c["areas"][0]["tracks"][0]).duration_seconds == 3
    assert "decoding is a separate" in c["validation"]


def test_unrelated_malformed_iso_and_missing_incompatible_backend(tmp_path):
    p = tmp_path / "not-sacd.iso"
    p.write_bytes(b"ordinary ISO")
    with pytest.raises(AudioError):
        iso_structure(p)
    make_iso(p)
    with pytest.raises(AudioError, match="Backend unavailable"):
        open_sacd(p, Settings(sacd_extract="absent-backend-for-test"))
    with pytest.raises(AudioError, match="Unsupported sacd_extract"):
        backend_capabilities(Settings(sacd_extract=sys.executable))
    with p.open("r+b") as f:
        f.seek(510 * 2048 + 64)
        f.write(b"\xff" * 4)
    with pytest.raises(AudioError, match="bounds"):
        iso_structure(p)


def test_listing_rejects_partial_or_malformed_times():
    for text in [
        listing().replace("Duration: 00:03:00", "Duration: 00:03:75"),
        listing().replace("Track Count: 1", "Track Count: 2"),
        listing().replace("Track_Start_Time_Code:", "Unknown:"),
    ]:
        with pytest.raises(AudioError):
            parse_listing(text)


def test_logical_cache_tracks_and_fingerprints(tone, tmp_path, settings, monkeypatch):
    from music_project.ui.shared import cached_analysis, clear_analysis_cache

    c = open_cue(cue_file(tmp_path, [tone.name], ["00:00:00", "00:01:00"]), settings)
    sources = [track_source(t) for t in c["tracks"]]
    calls = []
    monkeypatch.setattr(
        "music_project.ui.shared.analyze_source",
        lambda s, *a, **k: calls.append(s.track) or ("mock-result", None),
    )
    clear_analysis_cache()
    for s in [sources[0], sources[1], sources[0]]:
        st = Path(s.origin).stat()
        cached_analysis(s.origin, st.st_size, st.st_mtime_ns, settings, logical_source=s)
    assert calls == [1, 2]
    assert json.loads(json.dumps(sources[0].to_dict()))["start_75"] == 0


def test_repeated_file_is_not_double_counted(tone, tmp_path, settings):
    p = cue_file(tmp_path, [tone.name, tone.name])
    c = open_cue(p, settings)
    assert not any(t["status"] == "Ready" for t in c["tracks"])


def test_unresolved_encoding_and_global_construct_are_explicit(tone, tmp_path, settings):
    p = tmp_path / "broken.cue"
    p.write_bytes(b"\x98")
    with pytest.raises(AudioError, match="encoding"):
        parse_cue(p)
    p = cue_file(tmp_path, [tone.name])
    p.write_text("PREGAP 00:01:00\n" + p.read_text(encoding="utf-8"), encoding="utf-8")
    assert open_cue(p, settings)["tracks"][0]["status"] == "Unsupported"
    with pytest.raises(AudioError, match="encoding"):
        parse_cue(p, encoding="not-an-existing-encoding")


@pytest.mark.parametrize("kind", ["wav", "flac"])
def test_pcm_seek_and_fractional_cue_frames_preserve_selected_samples(
    tmp_path, write_wav, encode, settings, kind
):
    rng = np.random.default_rng(813)
    values = rng.integers(-10000, 10000, 48000 * 5, dtype=np.int32)
    audio = write_wav(tmp_path / "samples.wav", values / 32768)
    if kind == "flac":
        audio = encode(audio, tmp_path / "samples.flac", "-c:a", "flac")
    p = cue_file(tmp_path, [audio.name], ["00:00:00", "00:03:01", "00:04:01"])
    source = track_source(open_cue(p, settings)["tracks"][1])
    r, context = analyze_source(source, settings)
    first = (3 * 75 + 1) * 640
    assert np.array_equal(context.samples[:, 0], values[first : first + 48000] / 32768)
    assert r.findings["logical_source"].measurements["source_start_seconds"] == first / 48000


def test_native_cancel_and_temporary_budget(tmp_path, settings):
    audio = dsf(tmp_path / "native.dsf", rate=2822400, seconds=0.2)
    source = track_source(open_cue(cue_file(tmp_path, [audio.name]), settings)["tracks"][0])
    with pytest.raises(AudioError, match="budget"):
        analyze_source(source, replace(settings, max_track_bytes=1))
    with pytest.raises(AudioError, match="Cancelled"):
        analyze_source(source, settings, cancelled=lambda: True)


@pytest.mark.parametrize("failure", ["decoder", "extra-output", "invalid-output"])
def test_sacd_extraction_failure_cleans_only_owned_temporary_files(
    tmp_path, settings, monkeypatch, failure
):
    from music_project.core.source_models import AudioSource, fingerprints
    from music_project.core.subprocess_utils import CommandResult

    iso = make_iso(tmp_path / "synthetic.iso")
    source = AudioSource(
        "sacd", str(iso), str(iso), 1, "Track", "", 150, 375, 3, "stereo", fingerprints([iso])
    )
    area = {
        "kind": "stereo",
        "native_rate_hz": 2822400,
        "channels": 2,
        "encoding": "DST",
        "tracks": [{"source": source.to_dict()}],
    }
    monkeypatch.setattr(
        "music_project.core.sacd.open_sacd",
        lambda *a: {"areas": [area], "backend_version": "mocked-protocol"},
    )
    monkeypatch.setattr(
        "music_project.core.sacd.backend_capabilities",
        lambda *a: {"executable": "mock", "output_option": "-y"},
    )
    folders = []

    def fail(command, **kwargs):
        folder = Path(kwargs["cwd"])
        folders.append(folder)
        if failure == "decoder":
            raise AudioError("mock extraction failure")
        (folder / "one.dsf").write_bytes(b"invalid DSF")
        if failure == "extra-output":
            (folder / "two.dsf").write_bytes(b"invalid DSF")
        return CommandResult(b"", "")

    monkeypatch.setattr("music_project.core.sacd.run", fail)
    with pytest.raises(AudioError):
        analyze_source(source, settings)
    assert folders and not folders[0].exists()
    assert iso.exists()
