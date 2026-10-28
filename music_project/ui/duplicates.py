import streamlit as st

from music_project.core.library import duplicate_groups
from music_project.ui.shared import export_json, records

rows = records()
for field, title in (
    ("sha256", "Точное совпадение файлов"),
    ("pcm_sha256", "Совпадение canonical PCM"),
):
    st.subheader(title)
    groups = duplicate_groups(rows, field)
    if not groups:
        st.info("Группы не найдены в текущем индексе.")
    else:
        st.metric("Избыточные байты в этой категории", sum(g["redundant_bytes"] for g in groups))
        st.dataframe(groups, alt=title)
        export_json(f"Скачать {field} группы", groups, f"duplicates-{field}.json")
st.caption("Категории могут пересекаться; суммы нельзя складывать. Никакие файлы не удаляются.")
st.info(
    "Acoustic similarity: standalone fpcalc пока не интегрирован. Similarity не равна identity."
)
