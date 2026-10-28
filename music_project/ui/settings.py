import streamlit as st

from music_project import METHOD_VERSION, __version__
from music_project.core.config import Settings
from music_project.core.subprocess_utils import backend_versions

current = st.session_state.settings
with st.form("settings_form"):
    ffmpeg = st.text_input("FFmpeg executable", current.ffmpeg)
    ffprobe = st.text_input("ffprobe executable", current.ffprobe)
    sacd = st.text_input("sacd_extract executable (optional)", current.sacd_extract)
    fpcalc = st.text_input("fpcalc executable (optional)", current.fpcalc)
    seconds = st.number_input(
        "Начальный фрагмент для PCM-анализа, с", 1, 120, int(current.analysis_seconds)
    )
    timeout = st.number_input("Тайм-аут одного backend, с", 10, 7200, int(current.timeout))
    submitted = st.form_submit_button("Применить к текущей сессии")
if submitted:
    st.session_state.settings = Settings(
        ffmpeg, ffprobe, sacd, fpcalc, float(timeout), float(seconds)
    )
    st.success("Настройки применены. Для новых измерений повторно нажмите «Анализировать».")
st.text(f"Application {__version__} · Method {METHOD_VERSION}")
if st.button("Проверить backends"):
    st.json(backend_versions(st.session_state.settings))
st.caption(
    "Без учётной записи, обязательной телеметрии и отправки аудио. Настройки хранятся в сессии."
)
