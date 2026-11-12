"""Album browsing and track selection; decoding is an explicit action."""

from pathlib import Path

import streamlit as st

from music_project.core.config import backend_identity
from music_project.core.cue import open_cue, parse_cue, track_source
from music_project.core.models import AudioError
from music_project.core.sacd import open_sacd
from music_project.core.source_models import SOURCE_VERSION, fingerprints
from music_project.ui.shared import export_json

TRACK_STATUS = {
    "Ready": "Да",
    "Invalid": "Некорректные границы",
    "Missing": "Файл не найден",
    "Ambiguous": "Неоднозначно",
    "Authorization required": "Нужно разрешение",
    "Unsupported": "Не поддерживается",
    "Resolved": "Требуется проверка",
}


@st.cache_data(max_entries=4, ttl=600, show_spinner=False)
def _catalog(path, identity, settings, backend, roots, encoding, method):
    return (
        open_cue(Path(path), settings, authorized_roots=roots, encoding=encoding)
        if Path(path).suffix.lower() == ".cue"
        else open_sacd(Path(path), settings)
    )


def open_album(path, settings, *, roots=(), encoding=None, force=False):
    paths = [Path(path)]
    if Path(path).suffix.lower() == ".cue":
        parsed = parse_cue(Path(path), authorized_roots=roots, encoding=encoding)
        paths.extend(Path(f["path"]) for f in parsed["files"] if f.get("exists"))
        # Directory mtime invalidates Missing/Ambiguous resolutions when names change.
        paths.append(Path(path).parent)
        paths.extend(Path(root) for root in roots if Path(root).is_dir())
    if force:
        _catalog.clear()
    return _catalog(
        str(path),
        fingerprints(paths),
        settings,
        backend_identity(settings),
        tuple(roots),
        encoding,
        SOURCE_VERSION,
    )


def show_album(catalog):
    meta = catalog["metadata"]
    st.subheader(
        " · ".join(
            x
            for x in [
                meta.get("performer", meta.get("artist", "")),
                meta.get("title", Path(catalog["path"]).stem),
            ]
            if x
        )
    )
    if "areas" in catalog:
        choices = [a["kind"] for a in catalog["areas"]]
        selected = st.selectbox(
            "Область SACD",
            choices,
            format_func=lambda x: "Стерео" if x == "stereo" else "Многоканальная",
            key="album_area",
        )
        area = next(a for a in catalog["areas"] if a["kind"] == selected)
        tracks = area["tracks"]
        st.caption(
            f"SACD ISO · {area['encoding']} · {area['native_rate_hz'] or 'Неизвестно'} Hz · {area['channels']} каналов"
        )
    else:
        tracks = catalog["tracks"]
        st.caption(
            "CUE: границы INDEX 01; INDEX 00 сохранён отдельно. Формат FILE проверяется по аудиофайлу."
        )
    st.dataframe(
        [
            {
                "№": t["number"],
                "Название": t.get("title", ""),
                "Исполнитель": t.get("performer", ""),
                "Начало в источнике, s": round(t["start_seconds"], 6)
                if t.get("start_seconds") is not None
                else None,
                "Длительность, s": round(t["duration_seconds"], 6)
                if t.get("duration_seconds") is not None
                else None,
                "Доступна": TRACK_STATUS.get(t["status"], t["status"]),
            }
            for t in tracks
        ],
        hide_index=True,
        alt="Дорожки альбома, границы и доступность",
    )
    ready = [t for t in tracks if t["status"] == "Ready"]
    selected_source = None
    clicked = False
    if ready:
        index = st.selectbox(
            "Дорожка",
            range(len(ready)),
            format_func=lambda i: (
                f"{ready[i]['number']:02d}. {ready[i].get('title', '')} · {ready[i]['duration_seconds']:.3f} s"
            ),
            key="album_track_" + catalog["path"] + str(ready[0].get("source", {}).get("area", "")),
        )
        t = ready[index]
        st.caption(
            "Временные метки результатов — от начала выбранной дорожки. Полный анализ относится к дорожке, а не ко всему альбому."
        )
        selected_source = track_source(t)
        clicked = st.button("Анализировать дорожку", type="primary", key="analyze_album_track")
    else:
        st.info("Нет доступных дорожек. Проверьте ссылки, границы и поддержку формата.")
    with st.expander("Сведения CUE / SACD", expanded=False):
        st.json(catalog)
        export_json("Скачать структуру альбома", catalog, "album-structure.json")
    return selected_source, clicked


def open_album_message(path, settings, **options):
    try:
        return open_album(path, settings, **options)
    except (AudioError, OSError) as exc:
        if "Backend unavailable: sacd_extract" in str(exc):
            st.error(
                "sacd_extract не найден. В «Настройках» укажите путь к совместимому sacd_extract.exe. FFmpeg не заменяет SACD ISO extractor."
            )
        else:
            st.error("Не удалось открыть альбом: " + str(exc)[-600:])
        return None
