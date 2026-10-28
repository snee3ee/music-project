from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

PROJECT = Path(__file__).resolve().parents[1]


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.setenv("MUSIC_PROJECT_DB", str(tmp_path / "ui-index.sqlite3"))
    return AppTest.from_file(str(PROJECT / "app.py"), default_timeout=30).run()


@pytest.mark.parametrize(
    "page", ["home", "analyzer", "library", "duplicates", "compare", "archive", "tools", "settings"]
)
def test_navigation(app, page):
    app.switch_page(f"music_project/ui/{page}.py").run()
    assert not app.exception
    assert not app.error


def test_analyze_and_advanced_sections(app, tone):
    app.switch_page("music_project/ui/analyzer.py").run()
    app.text_input(key="analyzer_path").set_value(str(tone))
    app.form_submit_button[0].click().run()
    assert not app.exception and not app.error
    assert app.session_state.analysis_result[0] == "audio"
    assert any(e.label == "Quantization Structure" and not e.proto.expanded for e in app.expander)
    app.toggle(key="spectrum_visible").set_value(True).run()
    assert not app.exception and not app.error
    app.toggle(key="preview_visible").set_value(True).run()
    assert not app.exception and not app.error


def test_invalid_input_is_user_message(app, tmp_path):
    app.switch_page("music_project/ui/analyzer.py").run()
    app.text_input(key="analyzer_path").set_value(str(tmp_path / "missing.wav"))
    app.form_submit_button[0].click().run()
    assert app.error and not app.exception
    assert "Внутренняя ошибка" not in app.error[0].value


def test_ui_scan_and_dashboard(app, tone):
    app.switch_page("music_project/ui/library.py").run()
    app.text_input(key="library_folder").set_value(str(tone.parent))
    app.form_submit_button[0].click().run()
    assert not app.exception and not app.error
    assert app.success
    app.switch_page("music_project/ui/home.py").run()
    assert not app.exception and not app.error
    assert app.metric[0].value == "1"


def test_ui_compare(app, tone):
    app.switch_page("music_project/ui/compare.py").run()
    app.text_input(key="compare_a").set_value(str(tone))
    app.text_input(key="compare_b").set_value(str(tone))
    app.form_submit_button[0].click().run()
    assert not app.exception and not app.error
    assert app.session_state.comparison_result[2].measurements["identical_prefix"]
