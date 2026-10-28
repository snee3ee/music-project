from pathlib import Path

import streamlit as st

from music_project.core.compare import compare_pcm
from music_project.ui.shared import cached_analysis, export_json, show_finding

st.caption(
    "Сравнение первых фрагментов двух файлов. Историческая идентичность мастера не устанавливается."
)
with st.form("compare_form"):
    first = st.text_input("Файл A", key="compare_a")
    second = st.text_input("Файл B", key="compare_b")
    submitted = st.form_submit_button("Сравнить", type="primary")
if submitted:
    st.session_state.comparison_result = None
    results = []
    with st.spinner("Измеряем оба файла…"):
        for name in (first, second):
            path = Path(name.strip().strip('"')).resolve(strict=True)
            stat = path.stat()
            results.append(
                cached_analysis(
                    str(path), stat.st_size, stat.st_mtime_ns, st.session_state.settings
                )
            )
        (a, ca), (b, cb) = results
        if ca is None or cb is None:
            st.warning("Native DSD comparison не поддерживается.")
        else:
            st.session_state.comparison_result = (a, b, compare_pcm(ca, cb))
if st.session_state.comparison_result:
    a, b, finding = st.session_state.comparison_result
    show_finding("PCM comparison", finding)
    table = []
    for label, result in (("A", a), ("B", b)):
        p = result.findings["peaks"].measurements
        loud = result.findings["loudness"].measurements
        table.append(
            {
                "Файл": label,
                "Имя": result.info.name,
                "Длительность, с": result.info.duration,
                "Sample rate": result.info.sample_rate,
                "Bit depth": result.info.bit_depth,
                "Sample Peak, dBFS": p.get("sample_peak_dbfs"),
                "True Peak, dBTP": loud.get("true_peak_dbtp"),
                "LUFS": loud.get("integrated_lufs"),
                "LRA": loud.get("lra_lu"),
                "Crest, dB": p.get("crest_factor_db"),
            }
        )
    st.dataframe(table, alt="Объективные измерения двух файлов")
    export_json(
        "Скачать сравнение",
        {"a": a.to_dict(), "b": b.to_dict(), "comparison": finding.__dict__},
        "comparison.json",
    )
