import pandas as pd
import streamlit as st

from music_project.core.library import overview
from music_project.ui.presentation import codec_text
from music_project.ui.shared import records

rows = records()
st.caption("Библиотека: состав, размер, дубликаты и результаты последней проверки.")
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
        pd.DataFrame(
            [(codec_text(k), v) for k, v in stats["codecs"].items()], columns=["Codec", "Файлы"]
        ),
        x="Codec",
        y="Файлы",
        alt="Распределение файлов по кодекам",
    )
    with st.container(horizontal=True):
        st.metric("Файлы DSD", stats["dsd_files"], border=True)
        st.metric("Замечания к метаданным", stats["metadata_findings"], border=True)
    with st.expander("Sample rate и Bit depth", expanded=False):
        st.dataframe(
            [
                {
                    "Sample rate": f"{int(rate) / 1000:g} kHz" if int(rate) else "Нет данных",
                    "Файлы": count,
                }
                for rate, count in stats["sample_rates"].items()
            ],
            hide_index=True,
            alt="Распределение Sample rate",
        )
        st.dataframe(
            [
                {"PCM Bit depth": f"{bits}-bit" if bits != "None" else "Не указан", "Файлы": count}
                for bits, count in stats["bit_depths"].items()
            ],
            hide_index=True,
            alt="Распределение PCM Bit depth",
        )
    with st.expander("Хранение по кодекам и папкам альбомов", expanded=False):
        st.dataframe(
            [
                {"Codec": codec_text(k), "Размер, MiB": round(v / 2**20, 2)}
                for k, v in stats["storage_by_codec"].items()
            ],
            hide_index=True,
            alt="Размер библиотеки по Codec",
        )
        st.dataframe(
            [
                {"Папка альбома": k, "Размер, MiB": round(v / 2**20, 2)}
                for k, v in stats["storage_by_album_folder"].items()
            ],
            hide_index=True,
            alt="Размер библиотеки по папкам альбомов",
        )
    st.caption(
        "Индекс отражает последнее сканирование. Для строгой повторной проверки включите полный пересчёт."
    )
