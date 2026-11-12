from pathlib import Path

import pytest
from dsd_fixtures import dsf
from streamlit.testing.v1 import AppTest

PROJECT = Path(__file__).resolve().parents[1]


@pytest.fixture
def everyday(tmp_path, monkeypatch):
    monkeypatch.setenv("MUSIC_PROJECT_DB", str(tmp_path / "origin-ui.sqlite3"))
    return (
        AppTest.from_file(str(PROJECT / "app.py"), default_timeout=45)
        .run()
        .switch_page("music_project/ui/analyzer.py")
        .run()
    )


def analyze_file(app, path):
    app.text_input(key="analyzer_path").set_value(str(path))
    app.form_submit_button[0].click().run()
    assert not app.exception and not app.error
    return app.session_state.analysis_result[1][0].to_dict()


def test_everyday_is_default_and_mode_changes_preserve_results_without_analysis(
    everyday, tone, monkeypatch
):
    saved = analyze_file(everyday, tone)
    assert everyday.segmented_control(key="analysis_view").value == "everyday"
    visible = " ".join(e.value for group in (everyday.text, everyday.markdown) for e in group)
    assert "Целостность" in visible and "Происхождение" in visible
    assert "Technical Findings" not in visible
    assert not everyday.dataframe and not everyday.json

    def forbidden(*args, **kwargs):
        pytest.fail("Presentation switch must not run analysis or decoding")

    monkeypatch.setattr("music_project.ui.shared.analyze", forbidden)
    monkeypatch.setattr("subprocess.Popen", forbidden)
    everyday.segmented_control(key="analysis_view").set_value("expert").run()
    assert not everyday.exception
    everyday.segmented_control(key="analysis_module").set_value("provenance").run()
    everyday.toggle(key="origin_evidence_visible").set_value(True).run()
    assert everyday.dataframe and not everyday.exception
    assert everyday.session_state.analysis_result[1][0].to_dict() == saved
    everyday.segmented_control(key="analysis_view").set_value("everyday").run()
    assert not everyday.exception and not everyday.json
    assert everyday.session_state.analysis_result[1][0].to_dict() == saved


def test_everyday_full_action_really_runs_full_dsd(everyday, tmp_path):
    path = dsf(tmp_path / "generated.dsf", rate=2822400, seconds=0.3)
    analyze_file(everyday, path)
    assert not everyday.session_state.analysis_result[1][0].scope["complete_file"]
    everyday.segmented_control(key="analysis_module").set_value("integrity").run()
    everyday.button(key="origin_full").click().run()
    assert not everyday.exception and not everyday.error
    assert everyday.session_state.analysis_result[1][0].scope["complete_file"]
    assert everyday.session_state.analysis_result[1][0].info.duration_status == "Verified"


def test_reference_action_opens_workflow_and_executes_comparison(everyday, tone):
    saved = analyze_file(everyday, tone)
    everyday.segmented_control(key="analysis_module").set_value("provenance").run()
    everyday.button(key="origin_reference_next").click().run()
    assert not everyday.exception and everyday.toggle(key="origin_reference_visible").value
    everyday.text_input(key="origin_reference_path").set_value(str(tone))
    next(b for b in everyday.form_submit_button if b.label == "Сравнить референс").click().run()
    assert not everyday.exception and not everyday.error
    value = everyday.session_state.origin_reference_result
    assert value["status"] == "Measured" and value["alignment"]["measurements"]["identical_prefix"]
    assert everyday.session_state.analysis_result[1][0].to_dict() == saved
    assert not everyday.json
    everyday.segmented_control(key="analysis_module").set_value("appendix").run()
    everyday.selectbox(key="analysis_appendix").set_value("reference").run()
    import json

    assert json.loads(everyday.json[0].value) == value
