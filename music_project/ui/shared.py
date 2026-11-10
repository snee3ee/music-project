import json
import os
from collections import deque
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from pathlib import Path

import streamlit as st

from music_project import METHOD_VERSION
from music_project.core.analysis import analyze
from music_project.core.conclusion_models import CONCLUSIONS_VERSION, TECHNICAL_VERSION
from music_project.core.config import Settings, backend_identity
from music_project.core.dsd import DSD_METHOD_VERSION
from music_project.core.library import Library
from music_project.core.models import AudioError, Finding
from music_project.core.origin_models import ORIGIN_VERSION
from music_project.ui.presentation import measurement_rows, status_text

PROJECT = Path(__file__).resolve().parents[2]


def library() -> Library:
    # Test/automation override is explicitly limited to an index file, never audio.
    return Library(os.environ.get("MUSIC_PROJECT_DB", str(PROJECT / "data/library.sqlite3")))


def records() -> list[dict]:
    return library().records(st.session_state.get("library_root") or None)


def export_json(label: str, value: dict | list, filename: str):
    st.download_button(
        label,
        json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False),
        file_name=filename,
        mime="application/json",
    )


def cached_analysis(path: str, size: int, mtime_ns: int, settings: Settings, *, progress=None):
    stat = Path(path).stat()
    if (stat.st_size, stat.st_mtime_ns) != (size, mtime_ns):
        raise AudioError("Файл изменился; результат не сохранён в кэше")
    arguments = (
        path,
        size,
        mtime_ns,
        settings,
        f"{METHOD_VERSION}/{DSD_METHOD_VERSION}/{ORIGIN_VERSION}/{TECHNICAL_VERSION}/{CONCLUSIONS_VERSION}",
        backend_identity(settings),
    )
    if progress is None:
        result = _cached_analysis(*arguments)
    else:
        # Cache workers only publish numbers. Main-thread UI writes stay outside
        # the cached function, so cache replay never captures an obsolete widget.
        latest = deque(maxlen=1)
        with ThreadPoolExecutor(max_workers=1, thread_name_prefix="audio-analysis") as pool:
            future = pool.submit(_cached_analysis, *arguments, _progress=latest.append)
            while True:
                try:
                    result = future.result(timeout=0.1)
                    break
                except TimeoutError:
                    if future.done():
                        raise
                    if latest:
                        progress(latest[-1])
        progress(1.0)
    stat = Path(path).stat()
    if (stat.st_size, stat.st_mtime_ns) != (size, mtime_ns):
        raise AudioError("Файл изменился; результат не сохранён в кэше")
    return result


def clear_analysis_cache():
    _cached_analysis.clear()


@st.cache_data(max_entries=2, ttl=600, show_spinner=False)
def _cached_analysis(
    path: str,
    size: int,
    mtime_ns: int,
    settings: Settings,
    method_identity: str,
    backend_key: str,
    _progress=None,
):
    result = analyze(path, settings, progress=_progress)
    stat = Path(path).stat()
    if (stat.st_size, stat.st_mtime_ns) != (size, mtime_ns):
        raise AudioError("Файл изменился; результат не сохранён в кэше")
    return result


def show_finding(label: str, finding: Finding, *, advanced: bool = False):
    if advanced:
        with st.expander(label, expanded=False):
            st.text(finding.summary)
            finding_details(finding)
        return
    with st.container(border=True):
        st.markdown(f"**{label}**")
        if finding.observations:
            show_observations(finding)
            if finding.status == "Medium suspicion":
                st.caption(
                    "Вывод об источнике: " + status_text(finding.status) + ". " + finding.summary
                )
        else:
            st.text(f"{status_text(finding.status)}. {finding.summary}")
        with st.expander("Подробные измерения и ограничения", expanded=False):
            if finding.status == "Ambiguous" and any(
                o.code in {"CUTOFF", "NYQUIST_BOUNDARY"} for o in finding.observations
            ):
                st.text("Вывод об истории файла: недостаточно специфичных признаков.")
            finding_details(finding)


def show_measurements(values: dict, *, label: str = "Измерения"):
    rows = measurement_rows(values)
    if rows:
        st.dataframe(rows, hide_index=True, alt=label)


def show_observations(finding: Finding):
    for observation in finding.observations:
        st.text(observation.summary)


def finding_details(finding: Finding):
    show_measurements(finding.measurements)
    if finding.method:
        st.caption(finding.method)
    for limitation in finding.limitations:
        st.caption(limitation)
    if finding.evidence:
        st.caption("Evidence flags: " + ", ".join(finding.evidence))
    st.caption(f"Версия метода: {finding.method_version}")
