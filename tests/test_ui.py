from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

PROJECT = Path(__file__).resolve().parents[1]


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.setenv("MUSIC_PROJECT_DB", str(tmp_path / "ui-index.sqlite3"))
    value = AppTest.from_file(str(PROJECT / "app.py"), default_timeout=30).run()
    value.session_state.analysis_view = (
        "expert"  # Preserve the existing expert-navigation regression matrix.
    )
    return value


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
    assert [e.label for e in app.expander] == [
        "Параметры анализа",
        "Сведения об источнике",
    ]
    assert not app.dataframe
    assert not app.json and not app.code
    app.segmented_control(key="analysis_module").set_value("provenance").run()
    app.toggle(key="origin_evidence_visible").set_value(True).run()
    assert any("Bit-depth / Padding" in e.value for e in app.markdown)
    app.segmented_control(key="analysis_module").set_value("measurements").run()
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


def test_choose_then_analyze_without_pasting_path(app, tone, monkeypatch):
    from music_project.ui import file_picker

    monkeypatch.setattr(file_picker, "choose_file", lambda: str(tone))
    app.switch_page("music_project/ui/analyzer.py").run()
    app.button(key="choose_audio").click().run()
    assert app.text_input(key="analyzer_path").value == str(tone)
    app.form_submit_button[0].click().run()
    assert not app.exception and not app.error
    assert app.session_state.analysis_result[1][0].info.path == str(tone.resolve())
    visible = " ".join(e.value for group in (app.text, app.caption, app.markdown) for e in group)
    assert "decoded_seconds" not in visible
    assert "Not applicable / Unknown" not in visible
    app.segmented_control(key="analysis_module").set_value("measurements").run()
    visible = " ".join(e.value for group in (app.text, app.caption, app.markdown) for e in group)
    assert "Отсчётов на цифровом пределе" in visible


def test_cancel_keeps_selected_file(app, tone, monkeypatch):
    from music_project.ui import file_picker

    monkeypatch.setattr(file_picker, "choose_file", lambda: None)
    app.session_state.analyzer_path = str(tone)
    app.switch_page("music_project/ui/analyzer.py").run()
    app.button(key="choose_audio").click().run()
    assert app.text_input(key="analyzer_path").value == str(tone)
    assert not app.exception and not app.error


def test_empty_file_selection_is_clear_error(app):
    app.switch_page("music_project/ui/analyzer.py").run()
    app.form_submit_button[0].click().run()
    assert app.error[0].value == "Сначала выберите файл для анализа."
    assert not app.exception


def test_dsd_diagnostics_and_full_mode(app, tmp_path):
    from dsd_fixtures import dsf

    path = dsf(tmp_path / "generated.dsf")
    app.switch_page("music_project/ui/analyzer.py").run()
    app.text_input(key="analyzer_path").set_value(str(path))
    app.selectbox(key="dsd_mode").set_value("full")
    app.selectbox(key="dsd_rate").set_value(176400)
    app.form_submit_button[0].click().run()
    assert not app.exception and not app.error
    result, context = app.session_state.analysis_result[1]
    assert context is None and result.scope["complete_file"]
    assert result.findings["dsd_integrity"].status == "Passed"
    assert "DSD Diagnostics" in app.segmented_control(key="analysis_module").options
    app.segmented_control(key="analysis_module").set_value("dsd").run()
    assert len(app.expander) == 1
    visible = " ".join(e.value for group in (app.text, app.caption, app.markdown) for e in group)
    assert "DST: Не применяется" in visible
    assert "Измеренный выход DSD-to-PCM" in visible
    app.segmented_control(key="analysis_module").set_value("measurements").run()
    app.toggle(key="dsd_psd").set_value(True).run()
    assert not app.exception and not app.error


def test_optional_dsd_decoder_failure_keeps_metadata(app, tmp_path):
    from dataclasses import replace

    from dsd_fixtures import dsf

    path = dsf(tmp_path / "generated.dsf")
    app.session_state.settings = replace(app.session_state.settings, ffmpeg="not-installed")
    app.switch_page("music_project/ui/analyzer.py").run()
    app.text_input(key="analyzer_path").set_value(str(path))
    app.form_submit_button[0].click().run()
    assert not app.exception
    assert any("MHz DSD" in c.value and "Кодек:" in c.value for c in app.caption)
    result = app.session_state.analysis_result[1][0]
    assert result.findings["dsd_conversion"].status == "Unsupported"


def test_pcm_module_switches_keep_results_and_cache_ffts(app, tone, monkeypatch):
    from music_project.ui import analysis_charts, shared

    app.switch_page("music_project/ui/analyzer.py").run()
    app.text_input(key="analyzer_path").set_value(str(tone))
    app.form_submit_button[0].click().run()
    original = app.session_state.analysis_result[1][0].to_dict()
    assert "DSD Diagnostics" not in app.segmented_control(key="analysis_module").options
    analysis_charts.pcm_spectrum_data.clear()
    analysis_charts.pcm_spectrogram_data.clear()
    calls = {"spectrum": 0, "spectrogram": 0}
    real_spectrum, real_spectrogram = analysis_charts.spectrum, analysis_charts.spectrogram

    def spectrum(context):
        calls["spectrum"] += 1
        return real_spectrum(context)

    def spectrogram(context):
        calls["spectrogram"] += 1
        return real_spectrogram(context)

    def forbidden(*args, **kwargs):
        pytest.fail("Presentation navigation must not invoke analysis/decoding")

    monkeypatch.setattr(analysis_charts, "spectrum", spectrum)
    monkeypatch.setattr(analysis_charts, "spectrogram", spectrogram)
    monkeypatch.setattr(shared, "cached_analysis", forbidden)
    monkeypatch.setattr("music_project.core.decoder.run", forbidden)
    for _ in range(2):
        app.segmented_control(key="analysis_module").set_value("measurements").run()
        app.toggle(key="spectrum_visible").set_value(True).run()
        app.segmented_control(key="analysis_module").set_value("overview").run()
        assert not app.exception and not app.error
    for module in ("integrity", "provenance", "appendix"):
        app.segmented_control(key="analysis_module").set_value(module).run()
        assert not app.exception and not app.error
    app.selectbox(key="analysis_appendix").set_value("spectrum").run()
    assert len(app.get("download_button")) == 2
    assert calls == {"spectrum": 1, "spectrogram": 1}
    assert app.session_state.analysis_result[1][0].to_dict() == original


def test_dsd_modules_and_appendix_preserve_exact_data_without_redecode(app, tmp_path, monkeypatch):
    import json

    from dsd_fixtures import dsf

    from music_project.ui import shared

    path = dsf(tmp_path / "generated.dsf")
    app.switch_page("music_project/ui/analyzer.py").run()
    app.text_input(key="analyzer_path").set_value(str(path))
    app.form_submit_button[0].click().run()
    original = app.session_state.analysis_result[1][0].to_dict()

    def forbidden(*args, **kwargs):
        pytest.fail("DSD presentation must not decode or analyze again")

    monkeypatch.setattr(shared, "cached_analysis", forbidden)
    monkeypatch.setattr("music_project.core.dsd_decoder.run", forbidden)
    monkeypatch.setattr("music_project.core.dsd_spectrum.StreamingWelch.consume", forbidden)
    assert not app.code and not app.json and not app.dataframe
    for module in ("integrity", "measurements", "provenance", "dsd", "appendix"):
        app.segmented_control(key="analysis_module").set_value(module).run()
        assert not app.exception and not app.error
        assert len(app.expander) <= 2  # Configuration and at most one optional result section.
    for section in ("results", "logs", "methods", "metadata", "spectrum", "raw"):
        app.selectbox(key="analysis_appendix").set_value(section).run()
        assert not app.exception and not app.error
    assert json.loads(app.json[0].value) == original
    assert len(app.get("download_button")) == 1
    assert app.session_state.analysis_result[1][0].to_dict() == original


def test_flac_new_modules(app, tone, tmp_path, encode):
    path = encode(tone, tmp_path / "fixture.flac")
    app.switch_page("music_project/ui/analyzer.py").run()
    app.text_input(key="analyzer_path").set_value(str(path))
    app.form_submit_button[0].click().run()
    assert any("Кодек: FLAC" in c.value for c in app.caption)
    for module in ("integrity", "measurements", "provenance", "appendix"):
        app.segmented_control(key="analysis_module").set_value(module).run()
        assert not app.exception and not app.error


def test_new_pcm_file_resets_dsd_navigation(app, tone, tmp_path):
    from dsd_fixtures import dsf

    path = dsf(tmp_path / "generated.dsf")
    app.switch_page("music_project/ui/analyzer.py").run()
    app.text_input(key="analyzer_path").set_value(str(path))
    app.form_submit_button[0].click().run()
    app.segmented_control(key="analysis_module").set_value("dsd").run()
    app.text_input(key="analyzer_path").set_value(str(tone))
    app.form_submit_button[0].click().run()
    assert not app.exception and not app.error
    assert app.segmented_control(key="analysis_module").value == "overview"
    assert "DSD Diagnostics" not in app.segmented_control(key="analysis_module").options


@pytest.mark.parametrize("mode,status", [("quick", "Derived"), ("full", "Verified")])
def test_dsf_selected_duration_and_secondary_estimate_in_appendix(app, tmp_path, mode, status):
    import json

    from dsd_fixtures import dsf, dsf_metadata

    path = dsf_metadata(dsf(tmp_path / "generated.dsf"), padding_bytes=500000)
    app.switch_page("music_project/ui/analyzer.py").run()
    app.text_input(key="analyzer_path").set_value(str(path))
    app.selectbox(key="dsd_mode").set_value(mode)
    app.form_submit_button[0].click().run()
    assert not app.exception and not app.error
    result = app.session_state.analysis_result[1][0]
    assert result.info.duration == 0.15 and result.info.duration_status == status
    selected = [c.value for c in app.caption if "Длительность:" in c.value]
    assert len(selected) == 1 and "Длительность: 0:00.15" in selected[0]
    assert str(round(result.info.ffprobe_duration, 2)) not in selected[0]
    # Status and alternate estimates stay in evidence, independent of compact layout.
    assert result.info.duration_status == ("Verified" if mode == "full" else "Derived")
    assert not app.json
    app.segmented_control(key="analysis_module").set_value("integrity").run()
    assert not app.json
    assert not any("Источник" in d.value.columns for d in app.dataframe)
    app.segmented_control(key="analysis_module").set_value("appendix").run()
    sources = json.loads(app.json[0].value)
    assert sources[0]["seconds"] == result.info.ffprobe_duration
    app.selectbox(key="analysis_appendix").set_value("raw").run()
    exported = json.loads(app.json[0].value)
    assert exported["info"]["duration"] == 0.15
    assert exported["info"]["ffprobe_duration"] > 0.15


def test_invalid_dsf_duration_is_not_replaced_by_estimate(app, tmp_path):
    import struct

    from dsd_fixtures import dsf

    path = dsf(tmp_path / "generated.dsf")
    data = bytearray(path.read_bytes())
    struct.pack_into("<Q", data, 12, len(data) + 100)
    path.write_bytes(data)
    app.switch_page("music_project/ui/analyzer.py").run()
    app.text_input(key="analyzer_path").set_value(str(path))
    app.form_submit_button[0].click().run()
    assert not app.exception and app.error
    result = app.session_state.analysis_result[1][0]
    assert result.info.duration is None and result.info.ffprobe_duration is not None
    selected = [c.value for c in app.caption if "Длительность:" in c.value]
    assert len(selected) == 1 and "Длительность: Не установлена" in selected[0]
