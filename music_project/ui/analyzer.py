from dataclasses import replace
from pathlib import Path

import streamlit as st

from music_project.core.disc import inspect_iso, parse_cue
from music_project.core.models import AudioError
from music_project.ui.analysis_views import show_analysis
from music_project.ui.file_picker import choose_file
from music_project.ui.presentation import cue_issue_text
from music_project.ui.shared import (
    cached_analysis,
    clear_analysis_cache,
    export_json,
    show_measurements,
)

st.caption("Выберите файл, запустите анализ и переключайтесь между модулями результатов.")
requested_full = st.session_state.pop("origin_full_requested", False)
requested_pcm_full = st.session_state.pop("technical_full_requested", False)
if requested_full:
    st.session_state.dsd_mode = "full"
if requested_pcm_full:
    st.session_state.technical_mode = "full"
if st.button("Выбрать файл…", icon=":material/folder_open:", key="choose_audio"):
    try:
        selected_path = choose_file()
        if selected_path:
            st.session_state.analyzer_path = selected_path
            st.session_state.analysis_result = None
    except AudioError as exc:
        st.warning(str(exc))
st.caption(
    "Откроется обычное окно выбора файла на этом компьютере. Можно также вставить путь ниже."
)
with st.form("analyze_form"):
    selected = st.text_input(
        "Выбранный файл",
        key="analyzer_path",
        placeholder="Выберите файл кнопкой выше или вставьте полный путь",
    )
    with st.expander("Параметры анализа", expanded=False):
        st.caption(
            "Эти настройки DSD применяются только к DSD-файлам. "
            "Quick: до трёх интервалов по 5 s. Full: весь поток до EOF."
        )
        dsd_mode = st.selectbox(
            "Область DSD-анализа",
            ["quick", "full"],
            format_func=lambda v: (
                "Quick Analysis — выбранные интервалы"
                if v == "quick"
                else "Full Analysis — весь поток"
            ),
            key="dsd_mode",
        )
        dsd_rate = st.selectbox(
            "Частота PCM для DSD-измерений",
            [352800, 176400],
            format_func=lambda v: f"{v / 1000:g} kHz",
            key="dsd_rate",
        )
        technical_mode = st.selectbox(
            "Область громкости и пиков PCM",
            ["full", "prefix"],
            format_func=lambda x: "Весь поток" if x == "full" else "Начальный фрагмент",
            key="technical_mode",
        )
        near_ceiling = st.number_input(
            "Порог около цифрового предела, dBFS",
            min_value=-60.0,
            max_value=0.0,
            value=-1.0,
            step=0.1,
            key="near_ceiling",
        )
        st.caption(
            "Порог и область применяются при следующем анализе PCM. В native DSD эти тесты не применяются."
        )
        force = st.checkbox("Повторить анализ без кэша", key="analysis_force")
    submitted = st.form_submit_button("Анализировать", type="primary")
if submitted or requested_full or requested_pcm_full:
    st.session_state.analysis_module = "overview"
    st.session_state.analysis_result = None
    st.session_state.origin_reference_result = None
    if not selected.strip():
        raise AudioError("Сначала выберите файл для анализа.")
    source = Path(selected.strip().strip(chr(34))).resolve(strict=True)
    if source.suffix.lower() == ".cue":
        st.session_state.analysis_result = ("cue", parse_cue(source))
    elif source.suffix.lower() == ".iso":
        st.session_state.analysis_result = ("iso", inspect_iso(source, st.session_state.settings))
    else:
        stat = source.stat()
        if force:
            clear_analysis_cache()
        settings = replace(
            st.session_state.settings,
            dsd_mode=dsd_mode,
            dsd_pcm_rate=dsd_rate,
            technical_mode=technical_mode,
            near_ceiling_dbfs=near_ceiling,
        )
        progress_bar = st.progress(0.0, text="Анализ аудиопотока…")
        try:
            with st.spinner("Измеряем параметры файла…"):
                result = cached_analysis(
                    str(source),
                    stat.st_size,
                    stat.st_mtime_ns,
                    settings,
                    progress=lambda value: progress_bar.progress(value),
                )
        finally:
            progress_bar.empty()
        st.session_state.analysis_result = ("audio", result)

stored = st.session_state.analysis_result
if stored:
    kind, value = stored
    if kind == "cue":
        st.subheader("CUE: структура альбома")
        show_measurements(
            {
                "Кодировка": value["encoding"].replace(
                    "fallback; verify metadata", "резервная; проверьте метаданные"
                ),
                **value["metadata"],
            }
        )
        st.dataframe(
            [
                {
                    "Файл": f["reference"],
                    "Ссылка допустима": "Да" if f["valid"] else "Нет",
                    "Файл существует": "Да" if f["exists"] else "Нет",
                }
                for f in value["files"]
            ],
            hide_index=True,
            alt="Файлы, указанные в CUE",
        )
        st.dataframe(
            [
                {
                    "Track": t["number"],
                    "Название": t.get("title", ""),
                    "Файл": t["file"] or "Ссылка отсутствует",
                    "INDEX 01, s": t["indexes"].get("01", 0) / 75
                    if "01" in t["indexes"]
                    else "Не указан",
                }
                for t in value["tracks"]
            ],
            hide_index=True,
            alt="Tracks и границы CUE",
        )
        for issue in value["issues"]:
            st.warning(cue_issue_text(issue))
        st.caption("Проверены метаданные и INDEX. Анализ аудио по отдельным Tracks не выполняется.")
        export_json("Скачать отчёт CUE", value, "cue-report.json")
    elif kind == "iso":
        st.subheader("ISO: распознавание образа")
        st.text(
            {
                "SACD signature detected": "Обнаружена сигнатура SACD.",
                "ISO9660; SACD not established": "Обнаружен ISO9660; сигнатура SACD не обнаружена.",
                "Unknown disc image": "Поддерживаемые сигнатуры образа не обнаружены.",
            }[value["type"]]
        )
        st.text(f"Размер: {value['size'] / 2**20:.2f} MiB")
        if value["backend"].startswith("Backend unavailable"):
            st.info("sacd_extract не найден. Чтение списка Tracks в этой версии не выполняется.")
        else:
            st.caption(
                "sacd_extract найден; чтение списка Tracks ещё не проверено и не подключено."
            )
        st.caption("Сигнатура не подтверждает исправность TOC или доступность аудио в образе.")
        export_json("Скачать отчёт ISO", value, "iso-report.json")
    else:
        result, context = value
        show_analysis(result, context)
