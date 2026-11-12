from dataclasses import replace
from pathlib import Path

import streamlit as st

from music_project.core.models import AudioError
from music_project.ui.album_sources import open_album_message, show_album
from music_project.ui.analysis_views import show_analysis
from music_project.ui.file_picker import choose_file
from music_project.ui.shared import (
    cached_analysis,
    clear_analysis_cache,
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
            st.session_state.album_catalog = None
            st.session_state.logical_selection = None
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
        cue_encoding = st.selectbox(
            "Кодировка CUE",
            ["auto", "utf-8-sig", "utf-16", "cp1251", "cp1252"],
            format_func=lambda v: "Авто: BOM / UTF-8 / cp1251" if v == "auto" else v,
            key="cue_encoding",
        )
        external_roots = st.text_area(
            "Разрешённые внешние каталоги CUE",
            key="cue_authorized_roots",
            help="По одному абсолютному пути в строке. Заполняя поле, вы разрешаете читать ссылки CUE внутри этих каталогов. По умолчанию разрешён только каталог CUE.",
        )
    submitted = st.form_submit_button("Анализировать", type="primary")

settings = replace(
    st.session_state.settings,
    dsd_mode=dsd_mode,
    dsd_pcm_rate=dsd_rate,
    technical_mode=technical_mode,
    near_ceiling_dbfs=near_ceiling,
)
to_analyze = None
logical_source = (
    st.session_state.get("logical_selection") if requested_full or requested_pcm_full else None
)
if submitted or requested_full or requested_pcm_full:
    st.session_state.analysis_module = "overview"
    st.session_state.analysis_result = None
    st.session_state.origin_reference_result = None
    if not selected.strip():
        raise AudioError("Сначала выберите файл для анализа.")
    source = Path(selected.strip().strip(chr(34))).resolve(strict=True)
    if logical_source is not None:
        to_analyze = Path(logical_source.origin)
    elif source.suffix.lower() in {".cue", ".iso"}:
        roots = tuple(p.strip().strip(chr(34)) for p in external_roots.splitlines() if p.strip())
        st.session_state.album_catalog = open_album_message(
            source,
            settings,
            roots=roots,
            encoding=None if cue_encoding == "auto" else cue_encoding,
            force=force,
        )
        st.session_state.logical_selection = None
    else:
        st.session_state.album_catalog = None
        st.session_state.logical_selection = None
        to_analyze = source

catalog = st.session_state.get("album_catalog")
if catalog:
    candidate, clicked = show_album(catalog)
    if candidate != st.session_state.get("logical_selection") and not (
        requested_full or requested_pcm_full
    ):
        st.session_state.analysis_result = None
    if clicked:
        logical_source = candidate
        st.session_state.logical_selection = candidate
        st.session_state.analysis_result = None
        st.session_state.analysis_module = "overview"
        to_analyze = Path(candidate.origin)

if to_analyze is not None:
    if force:
        clear_analysis_cache()
    stat = to_analyze.stat()
    progress_bar = st.progress(0.0, text="Анализ выбранного аудиопотока…")
    try:
        with st.spinner("Измеряем параметры…"):
            value = cached_analysis(
                str(to_analyze),
                stat.st_size,
                stat.st_mtime_ns,
                settings,
                progress=lambda v: progress_bar.progress(v),
                logical_source=logical_source,
            )
    finally:
        progress_bar.empty()
    st.session_state.analysis_result = ("audio", value)

stored = st.session_state.analysis_result
if stored and stored[0] == "audio":
    show_analysis(*stored[1])
