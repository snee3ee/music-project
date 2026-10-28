import json
from pathlib import Path

import streamlit as st

from music_project.core.integrity import create_manifest, verify_manifest
from music_project.core.models import AudioError
from music_project.ui.shared import export_json

st.caption(
    "SHA-256 всех обычных файлов папки. Ссылки и junctions исключены. Источники не изменяются."
)
with st.form("archive_form"):
    folder = st.text_input("Папка архива", value=st.session_state.library_root, key="archive_root")
    action = st.selectbox("Операция", ["Создать манифест", "Проверить манифест"])
    manifest_path = st.text_input("Путь к JSON-манифесту (для проверки)")
    submitted = st.form_submit_button("Выполнить", type="primary")
if submitted:
    st.session_state.manifest_result = None
    root = Path(folder.strip().strip('"')).resolve(strict=True)
    with st.spinner("Вычисляем SHA-256…"):
        if action == "Создать манифест":
            st.session_state.manifest_result = create_manifest(root)
        else:
            source = Path(manifest_path.strip().strip('"'))
            if source.stat().st_size > 32 * 1024 * 1024:
                raise AudioError("Манифест превышает лимит 32 MiB")
            manifest = json.loads(source.read_text(encoding="utf-8-sig"))
            if not isinstance(manifest, dict):
                raise AudioError("Ожидался JSON-объект манифеста")
            st.session_state.manifest_result = verify_manifest(root, manifest)
result = st.session_state.manifest_result
if result is not None:
    if isinstance(result, list):
        st.dataframe(result, alt="Результаты проверки архива")
    else:
        st.success(f"Манифест создан: {len(result['files'])} файлов")
        st.caption("Сохраните манифест вне проверяемой папки, чтобы он не появлялся как New.")
    export_json(
        "Скачать JSON",
        result,
        "music-project-manifest.json"
        if isinstance(result, dict)
        else "music-project-verification.json",
    )
