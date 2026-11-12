"""New evidence in existing Origin navigation, without replaying backend work."""

from copy import deepcopy
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from tools.lossy_dataset import negative, original, write_pcm


def test_normal_expert_lossy_evidence_and_export_use_same_saved_facts(tmp_path, monkeypatch):
    monkeypatch.setenv("MUSIC_PROJECT_DB", str(tmp_path / "index.sqlite3"))
    path = write_pcm(
        tmp_path / "filtered.wav",
        negative(original(44100, seconds=4), 44100, "band-limited"),
        44100,
    )
    project = Path(__file__).resolve().parents[1]
    app = (
        AppTest.from_file(str(project / "app.py"), default_timeout=60)
        .run()
        .switch_page("music_project/ui/analyzer.py")
        .run()
    )
    app.text_input(key="analyzer_path").set_value(str(path))
    app.form_submit_button[0].click().run()
    app.segmented_control(key="analysis_module").set_value("provenance").run()
    assert not app.exception and not app.json
    saved = deepcopy(app.session_state.analysis_result[1][0].to_dict())
    visible = " ".join(e.value for group in [app.text, app.markdown, app.caption] for e in group)
    assert "Предыдущее lossy-кодирование" in visible and "Исторический кодек неизвестен" in visible
    assert "максимум" in visible and "по окнам" in visible

    def forbidden(*args, **kwargs):
        pytest.fail("Evidence navigation must use saved data")

    monkeypatch.setattr("subprocess.Popen", forbidden)
    app.segmented_control(key="analysis_view").set_value("expert").run()
    app.toggle(key="lossy_evidence_visible").set_value(True).run()
    for section in ["Полосы", "Переходы", "Окна", "Метод и ограничения"]:
        app.selectbox(key="lossy_evidence_section").set_value(section).run()
        assert not app.exception and not app.error and not app.json
        if section != "Метод и ограничения":
            assert app.dataframe
        assert app.session_state.analysis_result[1][0].to_dict() == saved
    app.segmented_control(key="analysis_module").set_value("appendix").run()
    app.selectbox(key="analysis_appendix").set_value("raw").run()
    assert app.json and not app.exception
