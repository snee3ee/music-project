import pandas as pd
import streamlit as st

from music_project.core.library import overview
from music_project.ui.shared import records

rows = records()
st.caption("SCAN → ANALYZE → FIND → EXPLAIN → COMPARE → VERIFY")
if not rows:
    st.info("Библиотека ещё не проиндексирована. Откройте «Библиотека» и укажите папку.")
else:
    stats = overview(rows)
    with st.container(horizontal=True):
        st.metric("Файлы", stats["files"], border=True)
        st.metric("Альбомы / папки", stats["albums"], border=True)
        st.metric("Артисты", stats["artists"], border=True)
        st.metric("Размер, GiB", f"{stats['bytes'] / 2**30:.3f}", border=True)
    with st.container(horizontal=True):
        st.metric("Длительность, ч", f"{stats['duration_seconds'] / 3600:.2f}", border=True)
        st.metric("Требуют проверки", stats["errors"], border=True)
        st.metric("Группы byte-дубликатов", stats["exact_duplicate_groups"], border=True)
        st.metric("Группы PCM-совпадений", stats["decoded_duplicate_groups"], border=True)
    st.bar_chart(
        pd.DataFrame(stats["codecs"].items(), columns=["Кодек", "Файлы"]),
        x="Кодек",
        y="Файлы",
        alt="Распределение файлов по кодекам",
    )
    st.json(
        {
            "sample_rates_hz": stats["sample_rates"],
            "pcm_bit_depths": stats["bit_depths"],
            "dsd_files": stats["dsd_files"],
            "metadata_findings": stats["metadata_findings"],
        }
    )
    with st.expander("Хранение по кодекам и папкам альбомов", expanded=False):
        st.json(
            {
                "bytes_by_codec": stats["storage_by_codec"],
                "bytes_by_album_folder": stats["storage_by_album_folder"],
            }
        )
    st.caption(
        "Индекс отражает последнее сканирование. Для строгой повторной проверки включите полный пересчёт."
    )
