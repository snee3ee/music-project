from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

PROJECT = Path(__file__).resolve().parents[1]


def test_album_selection_track_analysis_and_cached_view(tone, tmp_path, monkeypatch):
    monkeypatch.setenv("MUSIC_PROJECT_DB", str(tmp_path / "source-ui.sqlite3"))
    cue = tmp_path / "Album.cue"
    cue.write_text(
        f'TITLE "Album"\nFILE "{tone.name}" WAVE\nTRACK 01 AUDIO\nTITLE "First"\nINDEX 01 00:00:00\nTRACK 02 AUDIO\nTITLE "Second"\nINDEX 01 00:01:00\n',
        encoding="utf-8",
    )
    app = (
        AppTest.from_file(str(PROJECT / "app.py"), default_timeout=45)
        .run()
        .switch_page("music_project/ui/analyzer.py")
        .run()
    )
    app.text_input(key="analyzer_path").set_value(str(cue))
    app.form_submit_button[0].click().run()
    assert not app.exception and not app.error
    assert app.session_state.analysis_result is None
    assert len(app.dataframe[0].value) == 2
    selector = next(s for s in app.selectbox if s.label == "Дорожка")
    selector.set_value(1).run()
    app.button(key="analyze_album_track").click().run()
    assert not app.exception and not app.error
    result = app.session_state.analysis_result[1][0]
    assert result.info.duration == 2
    assert result.findings["logical_source"].measurements["track"] == 2
    visible = " ".join(c.value for c in app.caption)
    assert "Кодек:" in visible and "Каналы:" in visible
    assert result.info.container == "wav"
    saved = result.to_dict()

    def forbidden(*a, **k):
        pytest.fail("A view change must not launch a backend")

    monkeypatch.setattr("subprocess.Popen", forbidden)
    app.segmented_control(key="analysis_view").set_value("expert").run()
    assert not app.exception
    assert app.session_state.analysis_result[1][0].to_dict() == saved
    app.segmented_control(key="analysis_module").set_value("provenance").run()
    app.toggle(key="origin_reference_visible").set_value(True).run()
    assert not app.exception
    assert not any(f.key == "origin_reference_form" for f in app.get("form"))
    assert any("логической дорожки" in item.value for item in app.info)
    next(s for s in app.selectbox if s.label == "Дорожка").set_value(0).run()
    assert not app.exception and app.session_state.analysis_result is None


def test_iso_backend_error_is_actionable_and_no_fake_tracks(tmp_path, monkeypatch):
    from dataclasses import replace

    from test_sources import make_iso

    monkeypatch.setenv("MUSIC_PROJECT_DB", str(tmp_path / "missing-ui.sqlite3"))
    iso = make_iso(tmp_path / "synthetic.iso")
    app = (
        AppTest.from_file(str(PROJECT / "app.py"), default_timeout=45)
        .run()
        .switch_page("music_project/ui/analyzer.py")
        .run()
    )
    app.session_state.settings = replace(
        app.session_state.settings, sacd_extract="intentionally-absent-extractor"
    )
    app.text_input(key="analyzer_path").set_value(str(iso))
    app.form_submit_button[0].click().run()
    assert not app.exception
    assert any("sacd_extract не найден" in e.value for e in app.error)
    assert not any(s.label == "Дорожка" for s in app.selectbox)
