import logging
import os
import sqlite3
from pathlib import Path

import streamlit as st

from music_project.core.config import Settings
from music_project.core.models import AudioError

os.environ.setdefault("MPLCONFIGDIR", str(Path(__file__).resolve().parent / "data/matplotlib"))

st.set_page_config(page_title="Music Project", page_icon=":material/library_music:", layout="wide")
st.session_state.setdefault("settings", Settings())
st.session_state.setdefault("library_root", "")
st.session_state.setdefault("analysis_result", None)
st.session_state.setdefault("comparison_result", None)
st.session_state.setdefault("manifest_result", None)

pages = [
    ("home", "Обзор", "home"),
    ("analyzer", "Анализ файла", "graphic_eq"),
    ("library", "Библиотека", "library_music"),
    ("duplicates", "Дубликаты", "content_copy"),
    ("compare", "Сравнение", "compare_arrows"),
    ("archive", "Архив / проверка", "verified"),
    ("tools", "Инструменты", "build"),
    ("settings", "Настройки", "settings"),
]
page = st.navigation(
    [
        st.Page(f"music_project/ui/{name}.py", title=title, icon=f":material/{icon}:")
        for name, title, icon in pages
    ]
)
st.sidebar.caption("Music Project · 0.1.0\n\nЛокальный анализ. Исходные файлы сохраняются.")
st.title(page.title)
try:
    page.run()
except (AudioError, OSError, ValueError, sqlite3.Error) as exc:
    st.error(str(exc))
except Exception:
    logging.exception("Unexpected application error")
    st.error("Внутренняя ошибка. Подробности записаны в журнал сервера.")
