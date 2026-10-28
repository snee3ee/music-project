from dataclasses import asdict

import streamlit as st

from music_project.core.devices import DeviceProfile, compatibility
from music_project.ui.shared import records

st.subheader("Профиль устройства")
st.caption(
    "Укажите ограничения из документации устройства. Это проверка профиля, а не тест воспроизведения."
)
with st.form("device_form"):
    codecs = st.text_input("Кодеки через запятую", "flac,pcm_s16le,pcm_s24le,mp3,aac")
    rate = st.number_input(
        "Максимальная PCM sample rate, Hz", min_value=8000, max_value=768000, value=96000, step=1000
    )
    channels = st.number_input("Максимум каналов", min_value=1, max_value=32, value=2)
    bits = st.multiselect("PCM bit depths", [8, 16, 24, 32], default=[16, 24])
    dsd_rates = st.multiselect("Native DSD rates, Hz", [2822400, 5644800, 11289600, 22579200])
    submitted = st.form_submit_button("Проверить индекс")
if submitted:
    profile = DeviceProfile(
        "Пользовательский",
        tuple(c.strip() for c in codecs.split(",")),
        int(rate),
        tuple(bits),
        int(channels),
        tuple(dsd_rates),
    )
    from music_project.core.models import AudioInfo

    results = []
    for row in records():
        if row.get("info"):
            result = compatibility(AudioInfo(**row["info"]), profile)
            results.append({"path": row["path"], "status": result.status, "reason": result.summary})
    st.dataframe(results, alt="Совместимость файлов с пользовательским профилем")
    with st.expander("Параметры профиля"):
        st.json(asdict(profile))
st.info("Изменение тегов, переименование, конвертация и удаление в этой версии не выполняются.")
