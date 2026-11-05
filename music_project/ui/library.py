from pathlib import Path

import streamlit as st

from music_project.core.library import audit_metadata
from music_project.ui.presentation import codec_text, metadata_text, status_text
from music_project.ui.shared import export_json, library, records, show_measurements

with st.form("library_form"):
    folder = st.text_input(
        "Папка библиотеки", value=st.session_state.library_root, key="library_folder"
    )
    pcm_hash = st.checkbox("Вычислять canonical PCM hash", value=True)
    force = st.checkbox(
        "Проверить все файлы заново",
        value=False,
        help="Повторно проверяются новые/изменённые файлы и записи с прежними методами или backend-настройками. "
        "Изменения файла определяются по размеру и времени изменения.",
    )
    submitted = st.form_submit_button("Сканировать", type="primary")
st.caption(
    "Чтение файлов и полная проверка декодирования. На больших коллекциях это может занять время."
)
st.caption(
    "После обновления методов или декодеров записи пересчитываются при следующем сканировании; "
    "существующий индекс сохраняется до этого сканирования."
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
    show_measurements(summary, label="Результат сканирования")
    if summary["errors"]:
        st.warning(
            f"Требуют проверки: {summary['errors']}. Причины указаны в столбце «Диагностика»."
        )
rows = records()
if rows:
    st.dataframe(
        [
            {
                "Путь": r["path"],
                "Статус": status_text(r["status"]),
                "Размер, MiB": round(r["size"] / 2**20, 2),
                "Codec": codec_text(r.get("info", {}).get("codec", "")),
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
        st.caption("Различия могут быть намеренными. Альбом определяется по папке и Album tag.")
        st.dataframe(
            [{"Файл / папка": i["path"], "Замечание": metadata_text(i["finding"])} for i in issues],
            hide_index=True,
            alt="Замечания к метаданным",
        )
    export_json("Скачать индекс JSON", rows, "library-index.json")
