from copy import deepcopy
from dataclasses import replace

import pytest

from music_project.core.models import Analysis, Finding
from music_project.ui.analysis_presentation import (
    CATEGORIES,
    available_modules,
    band_rows,
    declared_duration,
    decoder_warnings,
    duration_sources,
    integrity_summary,
)


@pytest.fixture
def dsd_result(info):
    attempts = [
        {
            "start_seconds": start,
            "status": "Passed",
            "fatal_error": None,
            "warnings": [
                f"[in#0/dsf @ {index:016x}] [warning] Estimating duration from bitrate, this may be inaccurate"
            ],
        }
        for index, start in enumerate([0, 115, 230], 1)
    ]
    return Analysis(
        replace(info, kind="DSD", sample_rate=11289600, duration=235.881361),
        {"complete_file": False, "decoded_seconds": 15, "ranges": [{}, {}, {}]},
        {
            "dsd": Finding("Measured", "Native metadata"),
            "dsd_container": Finding(
                "Passed",
                "Container checked",
                {
                    "container": "DSF",
                    "errors": [],
                    "warnings": ["ffprobe minus container duration: 1.854694333 s"],
                    "expected_duration_seconds": 234.02666666666667,
                },
            ),
            "dsd_integrity": Finding(
                "Partial", "Quick", {"attempts": attempts, "successfully_decoded_seconds": 15}
            ),
            "dsd_audible": Finding("Measured", "Derived PCM"),
            "dsd_evidence": Finding("Ambiguous", "Unknown origin"),
        },
        {},
    )


def test_warning_group_preserves_all_events_and_intervals(dsd_result):
    original = deepcopy(dsd_result.to_dict())
    groups = decoder_warnings(dsd_result)
    assert len(groups) == 1 and groups[0].events == 3
    assert groups[0].intervals == [1, 2, 3]
    assert len(groups[0].raw_events) == 3
    assert "bitrate" in groups[0].summary
    assert all(" @ " in r["message"] for r in groups[0].raw_events)
    assert dsd_result.to_dict() == original


def test_distinct_warnings_not_suppressed(dsd_result):
    dsd_result.findings["dsd_integrity"].measurements["attempts"][0]["warnings"].append(
        "another warning"
    )
    groups = decoder_warnings(dsd_result)
    assert len(groups) == 2 and sum(g.events for g in groups) == 4


def test_duration_sources_do_not_replace_metadata_or_full_scope(dsd_result):
    assert declared_duration(dsd_result) == 234.02666666666667
    assert dsd_result.info.duration == 235.881361
    rows = duration_sources(dsd_result)
    assert [r["seconds"] for r in rows] == [235.881361, 234.02666666666667, 15]
    assert rows[-1]["complete_file"] is False
    summary = integrity_summary(dsd_result)
    assert summary["decode_status"] == "Partial" and not summary["complete_file"]
    assert summary["warning_events"] == 3 and not summary["fatal_errors"]


def test_pcm_and_unavailable_dsd_modules(info, dsd_result):
    pcm = Analysis(
        info,
        {"decoded_seconds": 3, "complete_file": True},
        {"peaks": Finding("Measured", "PCM")},
        {},
    )
    assert "dsd" not in available_modules(pcm)
    assert "provenance" not in available_modules(pcm)
    assert "measurements" in available_modules(pcm)
    assert not integrity_summary(pcm)["complete_file"]
    assert integrity_summary(pcm)["warning_events"] is None
    dsd_result.findings["dsd_audible"].status = "Unsupported"
    assert "measurements" not in available_modules(dsd_result)
    assert "dsd" in available_modules(dsd_result)


def test_backend_unavailable_is_not_fatal_decode(dsd_result):
    attempts = dsd_result.findings["dsd_integrity"].measurements["attempts"]
    attempts[0].update(status="Unsupported", fatal_error="Backend unavailable")
    attempts[1].update(status="Failed", fatal_error="Decoder failure")
    assert integrity_summary(dsd_result)["fatal_errors"] == ["Decoder failure"]


def test_band_display_units_silence_and_applicability():
    bands = [
        {
            "low_hz": 20000,
            "high_hz": 40000,
            "status": "Measured",
            "power_db_re_fs2": [-69.345, None],
            "power_fs2": [1e-7, 0],
            "left_minus_right_db": None,
        },
        {"low_hz": 100000, "high_hz": 140000, "status": "Unsupported", "power_db_re_fs2": None},
    ]
    original = deepcopy(bands)
    rows = band_rows(bands)
    assert len(rows) == 1
    assert rows[0]["Канал 1, dB re FS²"] == "-69.3"
    assert rows[0]["Канал 2, dB re FS²"] == "−∞"
    assert rows[0]["L−R, dB"] == "Не определено"
    assert all("dBFS" not in key for key in rows[0])
    assert len(band_rows(bands, measured_only=False)) == 2
    assert bands == original


def test_categories_are_distinct():
    assert len(CATEGORIES) == len(set(CATEGORIES.values())) == 9
