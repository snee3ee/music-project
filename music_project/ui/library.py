from pathlib import Path

import streamlit as st

from music_project.core.library import audit_metadata
from music_project.ui.shared import export_json, library, records

with st.form("library_form"):
    folder = st.text_input(
        "Папка библиотеки", value=st.session_state.library_root, key="library_folder"
    )
    pcm_hash = st.checkbox("Вычислять canonical PCM hash", value=True)
    force = st.checkbox("Полный пересчёт (иначе size + mtime_ns)", value=False)
    submitted = st.form_submit_button("Сканировать", type="primary")
st.caption(
    "Чтение файлов и полная проверка декодирования. На больших коллекциях это может занять время."
)
if submitted:
    root = Path(folder.strip().strip('"')).resolve(strict=True)
    st.session_state.library_root = str(root)
    progress = st.empty()
    with st.spinner("Сканируем библиотеку…"):
        summary = library().scan(
            root,
            st.session_state.settings,
            audio_hash=pcm_hash,
            force=force,
            progress=lambda n, p: progress.text(f"{n}: {p}"),
        )
    st.success("Сканирование завершено")
    st.json(summary)
rows = records()
if rows:
    st.dataframe(
        [
            {
                "Путь": r["path"],
                "Статус": r["status"],
                "Байт": r["size"],
                "Кодек": r.get("info", {}).get("codec", ""),
                "Диагностика": r.get("error", ""),
                "Проверен": r["scanned"],
            }
            for r in rows
        ],
        hide_index=True,
        alt="Индекс файлов библиотеки",
    )
    issues = audit_metadata(rows)
    with st.expander(f"Метаданные и различия альбомов: {len(issues)}", expanded=False):
        st.caption("Различия могут быть намеренными. Группировка альбомов: папка + album tag.")
        st.dataframe(issues, hide_index=True, alt="Замечания к метаданным")
    export_json("Скачать индекс JSON", rows, "library-index.json")
