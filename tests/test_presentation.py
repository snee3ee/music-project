from music_project.ui.presentation import (
    codec_text,
    container_text,
    duration_text,
    format_value,
    measurement_rows,
    metadata_text,
    status_text,
)


def test_human_values_without_python_literals():
    assert format_value(True) == "Да"
    assert format_value(False) == "Нет"
    assert format_value([1, 0, 3]) == "1; 0; 3"
    assert format_value(None, "sample_peak_dbfs") == "−∞ (тишина)"
    assert format_value(1000000) == "1 000 000"
    assert format_value(0.125) == "0.125"


def test_structured_metrics_are_flattened_with_readable_labels():
    rows = measurement_rows(
        {"boundaries": [{"boundary_hz": 22050, "drop_db": 40.0}], "complete_file": False}
    )
    assert rows == [
        {"Показатель": "Nyquist boundaries 1 · Граница, Hz", "Значение": "22 050"},
        {"Показатель": "Nyquist boundaries 1 · Спад, dB", "Значение": "40"},
        {"Показатель": "Проверен весь файл", "Значение": "Нет"},
    ]


def test_zero_residual_is_distinct_from_unreliable_alignment():
    exact = measurement_rows({"residual_rms_dbfs_after_gain": None, "alignment_reliable": True})
    uncertain = measurement_rows(
        {"residual_rms_dbfs_after_gain": None, "alignment_reliable": False}
    )
    assert exact[0]["Значение"] == "−∞ (Residual равен нулю)"
    assert "не прошёл" in uncertain[0]["Значение"]


def test_terms_and_russian_explanations():
    assert codec_text("pcm_s24le") == "PCM (integer)"
    assert codec_text("flac") == "FLAC"
    assert codec_text("dsd_lsbf_planar") == "DSD"
    assert container_text("mov,mp4,m4a,3gp,3g2,mj2") == "семейство MP4 / M4A"
    assert status_text("Measured") == "Измерено"
    assert status_text("Hash mismatch") == "SHA-256 не совпадает"
    assert metadata_text("Missing title") == "Не заполнен tag title"
    assert metadata_text("Album differs: sample_rate") == "Различается Sample rate"
    assert duration_text(90.5) == "1:30.50"
    assert duration_text(3601.0) == "1:00:01.00"
