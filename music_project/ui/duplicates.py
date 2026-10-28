from pathlib import Path

import streamlit as st

from music_project.core.library import duplicate_groups
from music_project.ui.shared import export_json, records

rows = records()
st.caption(
    "File identity: совпадают все байты файла, включая метаданные. "
    "PCM identity: совпадают декодированные PCM данные; метаданные могут различаться."
)
for field, title in (
    ("sha256", "Точное совпадение файлов"),
    ("pcm_sha256", "Совпадение canonical PCM"),
):
    st.subheader(title)
    groups = duplicate_groups(rows, field)
    if not groups:
        st.info("Группы не найдены в текущем индексе.")
    else:
        st.metric(
            "Размер дополнительных копий, MiB",
            f"{sum(g['redundant_bytes'] for g in groups) / 2**20:.2f}",
        )
        for index, group in enumerate(groups, 1):
            with st.expander(
                f"Группа {index} · {group['count']} файлов · "
                f"{group['total_bytes'] / 2**20:.2f} MiB",
                expanded=False,
            ):
                st.dataframe(
                    [{"Файл": Path(p).name, "Путь": p} for p in group["paths"]],
                    hide_index=True,
                    alt=f"Файлы группы {index}: {title}",
                )
                st.caption("SHA-256: " + group["hash"])
        export_json(
            "Скачать группы: " + ("File identity" if field == "sha256" else "PCM identity"),
            groups,
            f"duplicates-{field}.json",
        )
st.caption("Категории могут пересекаться; суммы нельзя складывать. Никакие файлы не удаляются.")
st.info(
    "Acoustic similarity в этой версии не выполняется. Здесь показаны File identity и PCM identity."
)
