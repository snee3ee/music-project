"""Integrity has one primary result and one optional evidence section."""

import streamlit as st

from music_project.ui.presentation import status_text
from music_project.ui.result_summary import integrity_view


def show_integrity(result, *, expert=False):
    summary = integrity_view(result)
    st.markdown(f"### {summary['headline']}")
    if summary["detail"]:
        st.text(summary["detail"])
    warnings = summary["warning_events"]
    warning_label = str(warnings) if warnings is not None else "не сохранены"
    errors = len(summary["fatal_errors"]) + len(summary["container_errors"])
    if summary["flac"].get("md5_status") == "Failed":
        errors += 1
    if summary["flac"].get("frame_count_status") == "Failed":
        errors += 1
    st.caption(f"{summary['coverage']} · предупреждения: {warning_label} · ошибки: {errors}")
    if not summary["complete_file"] and result.info.kind != "DSD":

        def full():
            st.session_state.technical_full_requested = True

        st.button("Измерить весь PCM-поток", key="technical_full", on_click=full)
    elif not summary["complete_file"] and result.info.kind == "DSD":
        from music_project.ui.origin import _request_full

        st.button(
            "Проверить всю дорожку"
            if "logical_source" in result.findings
            else "Проверить весь файл",
            on_click=_request_full,
            key="origin_full",
        )
    with st.expander("Сведения о проверке", expanded=False, on_change="rerun") as details:
        if not details.open:
            return
        st.text("Декодирование: " + status_text(summary["decode_status"]))
        st.text(
            "Контейнер: "
            + (
                "отдельно не проверялся"
                if result.info.kind != "DSD"
                else status_text(summary["container_status"])
            )
        )
        st.text(f"Прочитано / преобразовано: {summary['decoded_seconds']:.6f} s")
        f = summary["flac"]
        if f:
            st.text("FLAC MD5: " + status_text(f.get("md5_status", f.get("status", "Unknown"))))
            if f.get("expected_frames") is not None:
                st.text(
                    f"Кадры: объявлено {f['expected_frames']}, декодировано {f.get('decoded_frames', 'неизвестно')}"
                )
        ranges = result.scope.get("ranges", [])
        if ranges:
            st.dataframe(
                [
                    {
                        "Начало, s": r["start_seconds"],
                        "Прочитано, s": r["decoded_seconds"],
                        "Результат": status_text(r["status"]),
                    }
                    for r in ranges
                ],
                hide_index=True,
                alt="Фактически проверенные интервалы",
            )
        for group in summary["warning_groups"]:
            st.text(f"{group.summary} Событий: {group.events}.")
        if summary["container_warnings"]:
            st.text(f"Замечания структуры: {len(summary['container_warnings'])}.")
        st.caption("Исходные сообщения и параметры — в техническом приложении.")
