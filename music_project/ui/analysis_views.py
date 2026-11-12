"""One location per result; both modes navigate the same saved analysis."""

import streamlit as st

from music_project.ui.analysis_presentation import MODULES, available_modules
from music_project.ui.integrity_view import show_integrity
from music_project.ui.presentation import codec_text, container_text, duration_text
from music_project.ui.result_summary import (
    integrity_view,
    number_text,
    provenance_status,
    scope_label,
    signal_values,
)
from music_project.ui.signal_views import metric_row, show_levels


def cards(values):
    metric_row(values)


def file_identity(result):
    info = result.info
    logical = result.findings.get("logical_source")
    st.subheader((logical.measurements.get("title") or info.name) if logical else info.name)
    codec = (
        logical.measurements["extraction"]["source_encoding"]
        if logical and logical.measurements.get("kind") == "sacd"
        else codec_text(info.codec)
    )
    rate = (
        f"{info.sample_rate / 1e6:g} MHz DSD"
        if info.kind == "DSD"
        else f"{info.sample_rate / 1000:g} kHz"
    )
    parts = [f"Кодек: {codec}"]
    if info.bit_depth and info.kind != "DSD":
        parts.append(f"{info.bit_depth} бит")
    parts.extend(
        [
            rate if info.sample_rate else "Частота не установлена",
            f"Каналы: {info.channels}",
            "Длительность: "
            + (duration_text(info.duration) if info.duration is not None else "Не установлена"),
        ]
    )
    st.caption(" · ".join(parts))
    if logical:
        m = logical.measurements
        st.caption(
            f"Дорожка {m['track']} · начало в источнике {m['source_start_seconds']:.6f} s; время результатов — от начала дорожки."
        )


def show_overview(result):
    integrity = integrity_view(result)
    if integrity["failed"]:
        st.error("Проверка выявила ошибку; подробности — в «Целостности».")
    st.markdown(f"**Целостность:** {integrity['headline']}. {integrity['coverage']}.")
    st.markdown("**Происхождение:** " + provenance_status(result) + ".")
    loud, _ = signal_values(result)
    if loud:
        metric_row(
            [
                (label, number_text(loud, key))
                for key, label in [
                    ("integrated_lufs", "Integrated · LUFS"),
                    ("true_peak_dbtp", "True Peak · dBTP"),
                    ("lra_lu", "LRA · LU"),
                ]
            ]
        )
        st.caption("Громкость и пики: " + scope_label(loud.get("scope", {})))
    else:
        st.caption("Пригодных измерений громкости и True Peak нет.")
    with st.expander("Сведения об источнике", expanded=False, on_change="rerun") as details:
        if details.open:
            info = result.info
            st.text("Контейнер: " + container_text(info.container))
            st.text("Кодек: " + codec_text(info.codec))
            st.text(f"Размер источника: {info.size / 2**20:.2f} MiB")
            if info.bitrate:
                st.text(f"Bitrate: {info.bitrate / 1000:g} kb/s")
            st.text("Расположение: " + info.path)
            if info.tags:
                st.dataframe(
                    [{"Поле": k, "Значение": v} for k, v in info.tags.items()],
                    hide_index=True,
                    alt="Сохранённые метаданные источника",
                )


def show_measurements_module(result, context, *, expert=False):
    show_levels(result, context, expert=expert)


def show_provenance(result, *, expert=False):
    from music_project.ui.origin import show_origin_report

    show_origin_report(result, expert=expert)


def show_analysis(result, context):
    file_identity(result)
    view = st.segmented_control(
        "Уровень представления",
        ["everyday", "expert"],
        default=None if "analysis_view" in st.session_state else "everyday",
        format_func=lambda v: "Обычный" if v == "everyday" else "Эксперт",
        required=True,
        key="analysis_view",
    )
    options = available_modules(result)
    if st.session_state.get("analysis_module") not in options:
        st.session_state.analysis_module = "overview"
    module = st.segmented_control(
        "Модули анализа",
        options,
        format_func=MODULES.__getitem__,
        required=True,
        key="analysis_module",
        width="stretch",
    )
    expert = view == "expert"
    if module == "overview":
        show_overview(result)
    elif module == "integrity":
        show_integrity(result, expert=expert)
    elif module == "measurements":
        show_measurements_module(result, context, expert=expert)
    elif module == "provenance":
        show_provenance(result, expert=expert)
    elif module == "dsd":
        from music_project.ui.dsd import show_dsd

        show_dsd(result)
    elif module == "appendix":
        from music_project.ui.analysis_appendix import show_appendix

        show_appendix(result, context)
