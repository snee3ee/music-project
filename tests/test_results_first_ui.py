"""Presentation contracts: same saved facts, primary locations, no debug tables."""

import json
from copy import deepcopy
from pathlib import Path

import numpy as np
import pytest
from streamlit.testing.v1 import AppTest

from music_project.core.models import Analysis, Finding
from music_project.ui.result_summary import integrity_view, number_text, scope_label

PROJECT = Path(__file__).resolve().parents[1]


def test_missing_finite_and_infinite_display_are_distinct():
    assert number_text({}, "true_peak_dbtp") == "Не определено"
    assert number_text({"true_peak_state": "negative infinity"}, "true_peak_dbtp") == "−∞"
    assert number_text({"sample_peak_dbfs": None}, "sample_peak_dbfs") == "Не определено"
    assert number_text({}, "rms_dbfs", zero_is_silence=True) == "−∞"
    assert number_text({"lra_lu": 0}, "lra_lu") == "0.00"
    assert number_text({"lra_lu": float("nan")}, "lra_lu") == "Не определено"


def test_integrity_does_not_hide_digest_or_frame_count_failure(info):
    finding = Finding(
        "Failed",
        "",
        {
            "decode_status": "Passed",
            "complete_file": True,
            "decoded_seconds": 3,
            "flac_md5": {
                "status": "Failed",
                "md5_status": "Verified",
                "frame_count_status": "Failed",
            },
        },
    )
    result = Analysis(
        info,
        {"complete_file": True},
        {"pcm_integrity": finding, "logical_source": Finding("Derived", "")},
        {},
    )
    summary = integrity_view(result)
    assert summary["headline"] == "Проверка не пройдена"
    assert "MD5 совпал" in summary["detail"] and "число кадров различается" in summary["detail"]
    assert summary["coverage"] == "Вся выбранная дорожка"


def test_disjoint_and_unknown_scopes_are_not_full_files():
    assert scope_label({}) == "Область не установлена"
    assert scope_label({"ranges": [{}, {}, {}], "decoded_seconds": 15}) == "3 интервала · 15.000 s"
    assert (
        scope_label({"complete_file": True, "source_start_seconds": 90}) == "Вся выбранная дорожка"
    )


def app_for(path, tmp_path, monkeypatch):
    monkeypatch.setenv("MUSIC_PROJECT_DB", str(tmp_path / "clarity.sqlite3"))
    app = (
        AppTest.from_file(str(PROJECT / "app.py"), default_timeout=45)
        .run()
        .switch_page("music_project/ui/analyzer.py")
        .run()
    )
    app.text_input(key="analyzer_path").set_value(str(path))
    app.form_submit_button[0].click().run()
    assert not app.exception and not app.error
    return app


def test_primary_locations_and_all_evidence_survive_without_backends(tone, tmp_path, monkeypatch):
    app = app_for(tone, tmp_path, monkeypatch)
    saved = deepcopy(app.session_state.analysis_result[1][0].to_dict())
    assert not app.dataframe and not app.json
    assert [m.label for m in app.metric] == ["Integrated · LUFS", "True Peak · dBTP", "LRA · LU"]

    def forbidden(*a, **k):
        pytest.fail("UI navigation must not launch any backend")

    monkeypatch.setattr("subprocess.Popen", forbidden)
    for mode in ["expert", "everyday"]:
        app.segmented_control(key="analysis_view").set_value(mode).run()
        for module in ["overview", "integrity", "measurements", "provenance"]:
            app.segmented_control(key="analysis_module").set_value(module).run()
            assert not app.exception and not app.error and not app.json and not app.code
            for frame in app.dataframe:
                assert not {"Правило", "Версия", "rule_id"}.intersection(frame.value.columns)
            visible = " ".join(
                e.value for group in (app.text, app.caption, app.markdown) for e in group
            )
            assert "Technical Findings" not in visible
            if module == "overview":
                assert not app.dataframe and "### Пики" not in visible
            if module == "integrity":
                assert "Полное декодирование пройдено" in visible
                assert not app.metric
            if module == "measurements":
                assert "**Громкость**" in visible and "**Динамические измерения**" in visible
            if module == "provenance":
                assert "### Предыдущее lossy-кодирование" in visible
                assert "В доступной полосе нет применимых границ" not in visible
                assert "Полное декодирование:" not in visible
                assert "Порог поиска:" not in visible
            assert app.session_state.analysis_result[1][0].to_dict() == saved
    app.segmented_control(key="analysis_module").set_value("appendix").run()
    app.selectbox(key="analysis_appendix").set_value("conclusions").run()
    table = app.dataframe[0].value
    assert len(table) == len(saved["conclusions"]) and "Правило" in table.columns
    app.selectbox(key="analysis_appendix").set_value("raw").run()
    assert json.loads(app.json[0].value) == saved


def test_short_silence_has_no_invented_loudness(tmp_path, write_wav, monkeypatch):
    path = write_wav(tmp_path / "short.wav", np.zeros((2400, 2)))
    app = app_for(path, tmp_path, monkeypatch)
    values = {m.label: m.value for m in app.metric}
    assert values["Integrated · LUFS"] == "Не определено"
    assert values["True Peak · dBTP"] == "−∞"
    assert values["LRA · LU"] == "Не определено"
    app.segmented_control(key="analysis_module").set_value("measurements").run()
    values = {m.label: m.value for m in app.metric}
    assert values["RMS · dBFS"] == "−∞" and values["Crest Factor · dB"] == "Не определено"
    assert not app.get("image")  # Zero-valued PSD is not a blank plot near 0 dB.
    assert not app.exception
