import json
import os
from pathlib import Path

import streamlit as st

from music_project.core.analysis import analyze
from music_project.core.config import Settings
from music_project.core.library import Library
from music_project.core.models import Finding

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


@st.cache_data(max_entries=2, ttl=600, show_spinner=False)
def cached_analysis(path: str, size: int, mtime_ns: int, settings: Settings):
    return analyze(path, settings)


def show_finding(label: str, finding: Finding, *, advanced: bool = False):
    if advanced:
        with st.expander(label, expanded=False):
            st.markdown(f"**{finding.status}** — {finding.summary}")
            st.json(finding.measurements)
            st.caption(finding.method)
            for limitation in finding.limitations:
                st.caption(limitation)
            st.json({"evidence": finding.evidence, "method_version": finding.method_version})
        return
    with st.container(border=True):
        st.markdown(f"**{label}: {finding.status}**")
        st.text(finding.summary)
        with st.expander("Измерения, метод и ограничения", expanded=False):
            st.json(finding.measurements)
            st.caption(finding.method)
            for limitation in finding.limitations:
                st.caption(limitation)
            st.json({"evidence": finding.evidence, "method_version": finding.method_version})
