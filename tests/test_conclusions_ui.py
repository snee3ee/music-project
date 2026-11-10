from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

PROJECT = Path(__file__).resolve().parents[1]


@pytest.fixture
def app(tmp_path, monkeypatch, tone):
    monkeypatch.setenv("MUSIC_PROJECT_DB", str(tmp_path / "conclusions-ui.sqlite3"))
    a = (
        AppTest.from_file(str(PROJECT / "app.py"), default_timeout=45)
        .run()
        .switch_page("music_project/ui/analyzer.py")
        .run()
    )
    a.text_input(key="analyzer_path").set_value(str(tone))
    a.form_submit_button[0].click().run()
    assert not a.exception and not a.error
    return a


def test_reference_and_modes_use_identical_stored_measurements_without_backends(app, monkeypatch):
    saved = app.session_state.analysis_result[1][0].to_dict()

    def forbidden(*args, **kwargs):
        pytest.fail("Reference/view changes must not decode or analyze")

    monkeypatch.setattr("subprocess.Popen", forbidden)
    app.selectbox(key="technical_reference_widget").set_value("custom").run()
    assert not app.exception and not app.error
    profile = app.session_state.technical_reference
    assert profile.loudness_lufs == -14 and profile.peak_ceiling_dbtp == -1
    visible = " ".join(e.value for e in app.markdown)
    assert "Расчёт линейного gain" in visible
    assert app.session_state.analysis_result[1][0].to_dict() == saved
    app.segmented_control(key="analysis_view").set_value("expert").run()
    app.segmented_control(key="analysis_module").set_value("measurements").run()
    assert not app.exception
    app.toggle(key="conclusion_evidence_visible").set_value(True).run()
    assert app.json
    app.segmented_control(key="analysis_view").set_value("everyday").run()
    assert not app.exception and not app.json
    assert app.session_state.technical_reference == profile
    assert app.session_state.analysis_result[1][0].to_dict() == saved


def test_pcm_prefix_full_action_and_integrity_status(app):
    app.selectbox(key="technical_mode").set_value("prefix")
    app.form_submit_button[0].click().run()
    result = app.session_state.analysis_result[1][0]
    assert not result.findings["pcm_integrity"].measurements["complete_file"]
    app.segmented_control(key="analysis_view").set_value("expert").run()
    app.segmented_control(key="analysis_module").set_value("integrity").run()
    app.button(key="technical_full").click().run()
    assert not app.exception and not app.error
    assert (
        app.session_state.analysis_result[1][0]
        .findings["pcm_integrity"]
        .measurements["complete_file"]
    )


def test_no_reference_is_implicit_and_timelines_use_saved_data(app, monkeypatch):
    saved = app.session_state.analysis_result[1][0].to_dict()
    assert app.selectbox(key="technical_reference_widget").value == "none"
    assert not any(
        c.category == "reference" for c in app.session_state.analysis_result[1][0].conclusions
    )

    def forbidden(*args, **kwargs):
        pytest.fail("Plot display must not launch backends")

    monkeypatch.setattr("subprocess.Popen", forbidden)
    app.toggle(key="technical_timeline_visible").set_value(True).run()
    assert not app.exception
    assert len(app.get("image")) == 2
    assert app.session_state.analysis_result[1][0].to_dict() == saved
